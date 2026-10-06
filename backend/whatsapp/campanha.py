"""Motor de campanha: dispara a fila de leads com ritmo humano (intervalo
aleatório, pausa longa a cada N, janela de horário), respeitando o teto do
aquecimento e parando sozinho em 5 falhas seguidas. O estado fica 100% no
banco (não em memória) - é o que permite sobreviver a um restart.

Dependências injetáveis (monkeypatch nos testes, igual `db.CAMINHO_BANCO`):
`_evolution`, `_dormir`, `_agora`, `_aleatorio`. Com `_dormir` virando no-op e
`_agora` fixo, os testes tocam `processar_proximo()` direto, sem thread nem
espera de verdade.
"""

import json
import logging
import random
import re
import threading
import time
from datetime import datetime, timedelta

import db
import rotas_conversa
from rotas_leads import SQL_SCORE, calcular_score

from . import aquecimento, evolution, texto

logger = logging.getLogger(__name__)

# Dependências injetáveis - ver docstring do módulo.
_evolution = evolution
_dormir = time.sleep
_agora = datetime.now
_aleatorio = random.random

RITMO_PADRAO = {
    "intervalo_min_s": 45,
    "intervalo_max_s": 120,
    "pausa_a_cada": 10,
    "pausa_s": 600,
    "janela_inicio": "09:00",
    "janela_fim": "18:00",
}

STATUS_ATIVOS = ("rodando", "pausada", "interrompida")
ESTADOS_QUE_ESPERAM = ("aguardando_janela", "aguardando_teto", "aguardando_conexao")

# Estado "ao vivo" que não faz parte do contrato de colunas de wa_campanhas
# (proximo_envio_em/aguardando_janela): fica só em memória, se perde num
# restart - tudo bem, porque um restart já marca a campanha como
# 'interrompida' e esses dois campos só fazem sentido com status 'rodando'.
_estado_ao_vivo = {}

# thread única - só uma campanha roda por vez, de propósito.
_thread_ativa = None
# Só a thread da geração mais recente pode enviar (ver _rodar_em_thread).
_geracao_thread = 0
_lock_thread = threading.Lock()


# ---------------------------------------------------------------------------
# Consulta / leitura
# ---------------------------------------------------------------------------

def existe_campanha_ativa():
    conexao = db.conectar()
    try:
        linha = conexao.execute(
            "SELECT * FROM wa_campanhas WHERE status IN ('rodando','pausada','interrompida') "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
    finally:
        conexao.close()
    return dict(linha) if linha else None


def obter_campanha(campanha_id):
    conexao = db.conectar()
    try:
        linha = conexao.execute("SELECT * FROM wa_campanhas WHERE id = ?", (campanha_id,)).fetchone()
        if not linha:
            return None
        campanha_dict = dict(linha)
        ultimos = conexao.execute(
            "SELECT l.nome AS nome, we.telefone AS telefone, we.status AS status, we.enviado_em AS enviado_em "
            "FROM wa_envios we LEFT JOIN leads l ON l.place_id = we.place_id "
            "WHERE we.campanha_id = ? ORDER BY we.id DESC LIMIT 20",
            (campanha_id,),
        ).fetchall()
    finally:
        conexao.close()

    ao_vivo = _estado_ao_vivo.get(campanha_id, {})
    rodando = campanha_dict["status"] == "rodando"
    return {
        "id": campanha_dict["id"],
        "nome": campanha_dict["nome"],
        "status": campanha_dict["status"],
        "template": campanha_dict["template"],
        "total": campanha_dict["total"],
        "enviados": campanha_dict["enviados"],
        "falhas": campanha_dict["falhas"],
        "pulados": campanha_dict["pulados"],
        "proximo_envio_em": ao_vivo.get("proximo_envio_em") if rodando else None,
        "aguardando_janela": bool(ao_vivo.get("aguardando_janela")) if rodando else False,
        "ultimo_erro": campanha_dict["ultimo_erro"],
        "criada_em": campanha_dict["criada_em"],
        "finalizada_em": campanha_dict["finalizada_em"],
        "ultimos": [dict(u) for u in ultimos],
    }


def listar():
    conexao = db.conectar()
    try:
        linhas = conexao.execute("SELECT id FROM wa_campanhas ORDER BY id DESC LIMIT 50").fetchall()
        ativa_linha = conexao.execute(
            "SELECT id FROM wa_campanhas WHERE status IN ('rodando','pausada','interrompida') "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
    finally:
        conexao.close()
    historico = [obter_campanha(l["id"]) for l in linhas]
    ativa = obter_campanha(ativa_linha["id"]) if ativa_linha else None
    return {"ativa": ativa, "historico": historico}


# ---------------------------------------------------------------------------
# Filtro de leads (previa / criação de campanha)
# ---------------------------------------------------------------------------

def _query_base_leads(filtros):
    condicoes = ["(wa_optout IS NULL OR wa_optout = 0)", "telefone IS NOT NULL AND telefone != ''"]
    parametros = []

    status_lista = filtros.get("status") or ["novo"]
    marcadores = ",".join("?" for _ in status_lista)
    condicoes.append(f"status IN ({marcadores})")
    parametros.extend(status_lista)

    if filtros.get("nicho"):
        condicoes.append("nicho = ?")
        parametros.append(filtros["nicho"])
    if filtros.get("cidade"):
        condicoes.append("cidade = ?")
        parametros.append(filtros["cidade"])
    if filtros.get("sem_site"):
        condicoes.append("site_status = 'sem_site'")
    if filtros.get("sem_instagram"):
        condicoes.append("(instagram_url IS NULL OR instagram_url = '')")
    if filtros.get("max_avaliacoes") is not None:
        condicoes.append("COALESCE(num_avaliacoes, 0) <= ?")
        parametros.append(filtros["max_avaliacoes"])

    sql = "SELECT * FROM leads WHERE " + " AND ".join(condicoes) + f" ORDER BY {SQL_SCORE} DESC, nota DESC"
    return sql, parametros


def _telefones_ja_contatados(conexao):
    """União de quem já recebeu WhatsApp (wa_envios) com quem já tem mensagem
    nossa no cockpit (mensagens_conversa, autor vendedor) - a mesma pessoa
    pode ter recebido antes de este módulo existir."""
    vistos = set()
    for linha in conexao.execute("SELECT DISTINCT telefone FROM wa_envios WHERE status = 'enviado'"):
        canonico = rotas_conversa.normalizar_telefone(linha[0])
        if canonico:
            vistos.add(canonico)
    for linha in conexao.execute(
        "SELECT DISTINCT l.telefone FROM mensagens_conversa m "
        "JOIN leads l ON l.place_id = m.lead_ref "
        "WHERE m.canal = 'maps' AND m.autor = 'vendedor'"
    ):
        canonico = rotas_conversa.normalizar_telefone(linha[0])
        if canonico:
            vistos.add(canonico)
    return vistos


def telefone_ja_recebeu(telefone_evolution):
    """Trava de segurança absoluta (independe do filtro `pular_contatados`):
    nunca manda pro mesmo número duas vezes. Usada tanto pela campanha quanto
    pelo envio manual."""
    canonico = rotas_conversa.normalizar_telefone(telefone_evolution)
    if not canonico:
        return False
    conexao = db.conectar()
    try:
        return canonico in _telefones_ja_contatados(conexao)
    finally:
        conexao.close()


def _leads_filtrados(filtros, limite):
    sql, parametros = _query_base_leads(filtros)
    conexao = db.conectar()
    try:
        linhas = [dict(l) for l in conexao.execute(sql, parametros).fetchall()]
        pular_contatados = filtros.get("pular_contatados", True)
        ja_contatados = _telefones_ja_contatados(conexao) if pular_contatados else set()
    finally:
        conexao.close()

    score_min = filtros.get("score_min")
    score_max = filtros.get("score_max")
    so_celular = filtros.get("so_celular", True)

    descartados = {}

    def descartar(motivo):
        descartados[motivo] = descartados.get(motivo, 0) + 1

    aprovados = []
    for lead in linhas:
        lead["score"] = calcular_score(lead.get("nota"), lead.get("num_avaliacoes"), lead.get("site_status"))
        canonico = rotas_conversa.normalizar_telefone(lead.get("telefone"))
        if not canonico:
            descartar("telefone inválido")
            continue
        if so_celular and not (len(canonico) == 11 and canonico[2] == "9"):
            descartar("telefone fixo")
            continue
        if score_min is not None and lead["score"] < score_min:
            descartar("score abaixo do mínimo")
            continue
        if score_max is not None and lead["score"] > score_max:
            descartar("score acima do máximo")
            continue
        if canonico in ja_contatados:
            descartar("já recebeu mensagem antes")
            continue
        lead["_telefone_evolution"] = "55" + canonico
        aprovados.append(lead)

    total_aprovados = len(aprovados)
    if limite:
        aprovados = aprovados[: int(limite)]
    return aprovados, descartados, total_aprovados


def previa(filtros, template, limite):
    aprovados, descartados, _total = _leads_filtrados(filtros or {}, limite)
    teto = aquecimento.restantes_hoje()
    leads_resposta = [
        {
            "place_id": lead["place_id"],
            "nome": lead["nome"],
            "telefone": lead["telefone"],
            "nicho": lead.get("nicho"),
            "cidade": lead.get("cidade"),
            "score": lead["score"],
            "site_status": lead.get("site_status"),
            "texto_exemplo": texto.montar_mensagem(template, lead, rand=_aleatorio),
        }
        for lead in aprovados
    ]
    total = len(leads_resposta)
    aviso = None
    if total > teto:
        aviso = (
            f"A lista tem {total} contato(s), mas o teto de hoje é {teto}. "
            "A campanha continua sozinha amanhã, dentro da janela."
        )
    return {"leads": leads_resposta, "total": total, "descartados": descartados,
             "teto_restante": teto, "aviso": aviso}


# ---------------------------------------------------------------------------
# Ciclo de vida da campanha
# ---------------------------------------------------------------------------

def criar_campanha(nome, filtros, template, limite, ritmo, checar_whatsapp=True):
    """Cria a campanha (wa_campanhas + wa_fila) e já dispara a thread de
    envio. Pressupõe que as validações de 400 (link no template, campanha já
    ativa, WhatsApp desconectado, lista vazia) já rodaram na rota."""
    ritmo_completo = {**RITMO_PADRAO, **(ritmo or {})}
    aprovados, _descartados, _total = _leads_filtrados(filtros or {}, limite)

    agora = _agora().isoformat(timespec="seconds")
    config_json = json.dumps(
        {"filtros": filtros or {}, "ritmo": ritmo_completo, "checar_whatsapp": bool(checar_whatsapp)},
        ensure_ascii=False,
    )

    conexao = db.conectar()
    try:
        cursor = conexao.execute(
            "INSERT INTO wa_campanhas (nome, template, config_json, status, total, "
            "enviados, falhas, pulados, criada_em, atualizada_em) "
            "VALUES (?, ?, ?, 'rodando', ?, 0, 0, 0, ?, ?)",
            (nome or "Campanha", template, config_json, len(aprovados), agora, agora),
        )
        campanha_id = cursor.lastrowid
        for ordem, lead in enumerate(aprovados):
            texto_msg = texto.montar_mensagem(template, lead, rand=_aleatorio)
            conexao.execute(
                "INSERT INTO wa_fila (campanha_id, place_id, telefone, ordem, estado, texto) "
                "VALUES (?, ?, ?, ?, 'pendente', ?)",
                (campanha_id, lead["place_id"], lead["_telefone_evolution"], ordem, texto_msg),
            )
        conexao.commit()
    finally:
        conexao.close()

    _iniciar_thread(campanha_id)
    return obter_campanha(campanha_id)


def marcar_campanhas_interrompidas():
    """Chamado no startup do app (mesma ideia de `jobs.marcar_jobs_interrompidos`):
    campanha que ficou 'rodando' morreu junto com o processo anterior."""
    conexao = db.conectar()
    try:
        cursor = conexao.execute(
            "UPDATE wa_campanhas SET status = 'interrompida', atualizada_em = ? WHERE status = 'rodando'",
            (datetime.now().isoformat(timespec="seconds"),),
        )
        conexao.commit()
        if cursor.rowcount:
            logger.warning(
                "%s campanha(s) de WhatsApp estavam rodando quando o backend foi encerrado - "
                "marcadas como interrompidas", cursor.rowcount,
            )
    finally:
        conexao.close()


def parar(campanha_id):
    campanha_atual = obter_campanha(campanha_id)
    if not campanha_atual:
        return None, "campanha não encontrada"
    if campanha_atual["status"] not in ("rodando",):
        return None, "a campanha não está rodando"
    _atualizar_status(campanha_id, "pausada")
    return obter_campanha(campanha_id), None


def retomar(campanha_id):
    campanha_atual = obter_campanha(campanha_id)
    if not campanha_atual:
        return None, "campanha não encontrada"
    if campanha_atual["status"] not in ("pausada", "interrompida"):
        return None, "a campanha não está pausada nem interrompida"
    _atualizar_status(campanha_id, "rodando")
    _iniciar_thread(campanha_id)
    return obter_campanha(campanha_id), None


def descartar(campanha_id):
    campanha_atual = obter_campanha(campanha_id)
    if not campanha_atual:
        return None, "campanha não encontrada"
    conexao = db.conectar()
    try:
        conexao.execute(
            "UPDATE wa_fila SET estado = 'pulado' WHERE campanha_id = ? AND estado = 'pendente'",
            (campanha_id,),
        )
        conexao.commit()
    finally:
        conexao.close()
    _atualizar_status(campanha_id, "parada", finalizar=True)
    _estado_ao_vivo.pop(campanha_id, None)
    return obter_campanha(campanha_id), None


def _atualizar_status(campanha_id, status, ultimo_erro=None, finalizar=False):
    conexao = db.conectar()
    try:
        _sincronizar_contadores(conexao, campanha_id)
        agora = _agora().isoformat(timespec="seconds")
        if finalizar:
            conexao.execute(
                "UPDATE wa_campanhas SET status = ?, ultimo_erro = COALESCE(?, ultimo_erro), "
                "atualizada_em = ?, finalizada_em = ? WHERE id = ?",
                (status, ultimo_erro, agora, agora, campanha_id),
            )
        else:
            conexao.execute(
                "UPDATE wa_campanhas SET status = ?, ultimo_erro = COALESCE(?, ultimo_erro), "
                "atualizada_em = ? WHERE id = ?",
                (status, ultimo_erro, agora, campanha_id),
            )
        conexao.commit()
    finally:
        conexao.close()


def _sincronizar_contadores(conexao, campanha_id):
    linha = conexao.execute(
        "SELECT "
        " SUM(CASE WHEN estado='enviado' THEN 1 ELSE 0 END) AS enviados,"
        " SUM(CASE WHEN estado='falhou' THEN 1 ELSE 0 END) AS falhas,"
        " SUM(CASE WHEN estado='pulado' THEN 1 ELSE 0 END) AS pulados"
        " FROM wa_fila WHERE campanha_id = ?",
        (campanha_id,),
    ).fetchone()
    conexao.execute(
        "UPDATE wa_campanhas SET enviados = ?, falhas = ?, pulados = ? WHERE id = ?",
        (linha["enviados"] or 0, linha["falhas"] or 0, linha["pulados"] or 0, campanha_id),
    )


def _marcar_item(campanha_id, item_id, estado):
    conexao = db.conectar()
    try:
        conexao.execute("UPDATE wa_fila SET estado = ? WHERE id = ?", (estado, item_id))
        _sincronizar_contadores(conexao, campanha_id)
        conexao.commit()
    finally:
        conexao.close()


def _falhas_seguidas_atuais(campanha_id):
    """Recalculada a partir da cauda da fila (não é uma coluna própria) -
    assim sobrevive a um restart sem precisar de mais estado: o que importa é
    quantos 'falhou' seguidos vêm ANTES do primeiro item ainda pendente."""
    conexao = db.conectar()
    try:
        linhas = conexao.execute(
            "SELECT estado FROM wa_fila WHERE campanha_id = ? AND estado != 'pendente' ORDER BY ordem DESC",
            (campanha_id,),
        ).fetchall()
    finally:
        conexao.close()
    contagem = 0
    for linha in linhas:
        if linha["estado"] == "falhou":
            contagem += 1
        else:
            break
    return contagem


# ---------------------------------------------------------------------------
# Efeitos colaterais de um envio bem-sucedido/falho - porta única de saída de
# mensagem, usada tanto pela campanha quanto pelo envio manual (rotas_whatsapp).
# ---------------------------------------------------------------------------

def _registrar_envio_e_efeitos(place_id, telefone, texto_enviado, status, erro=None, campanha_id=None, id_externo=None):
    agora = _agora().isoformat(timespec="seconds")
    conexao = db.conectar()
    try:
        cursor = conexao.execute(
            "INSERT INTO wa_envios (place_id, telefone, texto, status, erro, campanha_id, id_externo, enviado_em) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (place_id, telefone, texto_enviado, status, erro, campanha_id, id_externo, agora),
        )
        envio_id = cursor.lastrowid

        if status == "enviado":
            # mesma chave que o webhook vai calcular se a Evolution ecoar essa
            # mensagem de volta como fromMe=true - assim não duplica no cockpit
            chave = rotas_conversa._chave_dedup("vendedor", texto_enviado, agora, id_externo)
            rotas_conversa._inserir_mensagem(conexao, "maps", place_id, "vendedor", texto_enviado, agora, "app", chave)

            lead_atual = conexao.execute("SELECT status FROM leads WHERE place_id = ?", (place_id,)).fetchone()
            if lead_atual and lead_atual["status"] == "novo":
                proximo = (_agora().date() + timedelta(days=3)).isoformat()
                conexao.execute(
                    "UPDATE leads SET status = 'contatado', proximo_followup = ?, atualizado_em = ? "
                    "WHERE place_id = ?",
                    (proximo, agora, place_id),
                )
                conexao.execute(
                    "INSERT INTO historico_status (place_id, status_anterior, status_novo, alterado_em) "
                    "VALUES (?, 'novo', 'contatado', ?)",
                    (place_id, agora),
                )

        conexao.commit()
        envio = dict(conexao.execute("SELECT * FROM wa_envios WHERE id = ?", (envio_id,)).fetchone())
    finally:
        conexao.close()

    if status == "enviado":
        aquecimento.marcar_inicio_se_necessario()
    return envio


def registrar_envio_manual(place_id, telefone, texto_enviado, status, erro=None, id_externo=None):
    """Ponto de entrada do envio manual (`POST /api/whatsapp/enviar`, fora de
    campanha) - mesmos efeitos colaterais do envio de campanha."""
    return _registrar_envio_e_efeitos(place_id, telefone, texto_enviado, status, erro=erro, id_externo=id_externo)


# ---------------------------------------------------------------------------
# Motor: um passo por chamada (testável sem thread nem sleep de verdade)
# ---------------------------------------------------------------------------

def _minutos(hhmm):
    try:
        horas, minutos = str(hhmm).split(":")
        return int(horas) * 60 + int(minutos)
    except (ValueError, AttributeError):
        return 0


def _dentro_da_janela(ritmo, agora_dt):
    inicio = _minutos(ritmo.get("janela_inicio") or "09:00")
    fim = _minutos(ritmo.get("janela_fim") or "18:00")
    minutos_agora = agora_dt.hour * 60 + agora_dt.minute
    return inicio <= minutos_agora < fim


def processar_proximo(campanha_id):
    """Processa um passo da campanha: um item da fila, ou uma espera (janela,
    teto do aquecimento, WhatsApp desconectado). Retorna o que aconteceu:
    'enviado' | 'falhou' | 'pulado' | 'aguardando_janela' | 'aguardando_teto' |
    'aguardando_conexao' | 'concluida' | 'pausada_por_falhas' | 'nao_esta_rodando'.
    """
    conexao = db.conectar()
    try:
        campanha_row = conexao.execute("SELECT * FROM wa_campanhas WHERE id = ?", (campanha_id,)).fetchone()
    finally:
        conexao.close()
    if not campanha_row or campanha_row["status"] != "rodando":
        return "nao_esta_rodando"

    config = json.loads(campanha_row["config_json"])
    ritmo = {**RITMO_PADRAO, **(config.get("ritmo") or {})}
    checar_whatsapp = config.get("checar_whatsapp", True)

    conexao = db.conectar()
    try:
        item = conexao.execute(
            "SELECT * FROM wa_fila WHERE campanha_id = ? AND estado = 'pendente' ORDER BY ordem LIMIT 1",
            (campanha_id,),
        ).fetchone()
        item = dict(item) if item else None
    finally:
        conexao.close()

    if item is None:
        _atualizar_status(campanha_id, "concluida", finalizar=True)
        _estado_ao_vivo.pop(campanha_id, None)
        return "concluida"

    estado_evolution = _evolution.estado()
    if not estado_evolution.get("conectado"):
        return "aguardando_conexao"
    if estado_evolution.get("numero_oficial"):
        # alguém trocou o chip no meio da campanha: para de vez, não espera
        _atualizar_status(
            campanha_id, "pausada",
            ultimo_erro="O WhatsApp conectado virou o seu número oficial. Campanha pausada.",
        )
        _estado_ao_vivo.pop(campanha_id, None)
        return "pausada_por_falhas"

    if not _dentro_da_janela(ritmo, _agora()):
        _estado_ao_vivo.setdefault(campanha_id, {})["aguardando_janela"] = True
        return "aguardando_janela"
    _estado_ao_vivo.setdefault(campanha_id, {})["aguardando_janela"] = False

    if aquecimento.restantes_hoje() <= 0:
        return "aguardando_teto"

    lead = _lead_do_item(item)
    if lead is None or lead.get("wa_optout"):
        _registrar_envio_e_efeitos(item["place_id"], item["telefone"], item["texto"], "pulado",
                                     erro="lead sem permissão de envio (optout)", campanha_id=campanha_id)
        _marcar_item(campanha_id, item["id"], "pulado")
        return "pulado"

    if telefone_ja_recebeu(item["telefone"]):
        _registrar_envio_e_efeitos(item["place_id"], item["telefone"], item["texto"], "pulado",
                                     erro="este número já tinha recebido mensagem antes", campanha_id=campanha_id)
        _marcar_item(campanha_id, item["id"], "pulado")
        return "pulado"

    if checar_whatsapp:
        mapa = _evolution.numeros_com_whatsapp([item["telefone"]])
        info = mapa.get(re.sub(r"\D", "", item["telefone"]))
        if info is not None and info.get("existe") is False:
            _registrar_envio_e_efeitos(item["place_id"], item["telefone"], item["texto"], "pulado",
                                         erro="sem WhatsApp", campanha_id=campanha_id)
            _marcar_item(campanha_id, item["id"], "pulado")
            return "pulado"

    try:
        resposta = _evolution.enviar_texto(item["telefone"], item["texto"])
    except Exception as erro:
        return _tratar_falha(campanha_id, item, str(erro))

    id_externo = (resposta.get("key") or {}).get("id") if isinstance(resposta, dict) else None
    _registrar_envio_e_efeitos(item["place_id"], item["telefone"], item["texto"], "enviado",
                                 campanha_id=campanha_id, id_externo=id_externo)
    _marcar_item(campanha_id, item["id"], "enviado")
    return "enviado"


def _lead_do_item(item):
    conexao = db.conectar()
    try:
        linha = conexao.execute("SELECT * FROM leads WHERE place_id = ?", (item["place_id"],)).fetchone()
    finally:
        conexao.close()
    return dict(linha) if linha else None


def _tratar_falha(campanha_id, item, mensagem_erro):
    _registrar_envio_e_efeitos(item["place_id"], item["telefone"], item["texto"], "falhou",
                                 erro=mensagem_erro, campanha_id=campanha_id)
    _marcar_item(campanha_id, item["id"], "falhou")

    falhas_seguidas = _falhas_seguidas_atuais(campanha_id)
    if falhas_seguidas >= aquecimento.FALHAS_QUE_TRAVAM_O_TETO:
        _atualizar_status(
            campanha_id, "pausada",
            ultimo_erro="Cinco falhas seguidas. A campanha parou sozinha para não queimar o número.",
        )
        _estado_ao_vivo.pop(campanha_id, None)
        return "pausada_por_falhas"
    return "falhou"


# ---------------------------------------------------------------------------
# Thread de fundo (uso real - os testes chamam processar_proximo direto)
# ---------------------------------------------------------------------------

def _dormir_intervalo(campanha_id, ritmo):
    minimo = max(1, int(ritmo.get("intervalo_min_s") or 45))
    maximo = max(minimo, int(ritmo.get("intervalo_max_s") or 120))
    segundos = minimo + _aleatorio() * (maximo - minimo)

    conexao = db.conectar()
    try:
        processados = conexao.execute(
            "SELECT COUNT(*) FROM wa_fila WHERE campanha_id = ? AND estado IN ('enviado','falhou')",
            (campanha_id,),
        ).fetchone()[0]
    finally:
        conexao.close()

    pausa_a_cada = int(ritmo.get("pausa_a_cada") or 0)
    if pausa_a_cada > 0 and processados > 0 and processados % pausa_a_cada == 0:
        segundos += int(ritmo.get("pausa_s") or 600)

    _estado_ao_vivo.setdefault(campanha_id, {})["proximo_envio_em"] = (
        _agora() + timedelta(seconds=segundos)
    ).isoformat(timespec="seconds")
    _dormir(segundos)
    _estado_ao_vivo.setdefault(campanha_id, {})["proximo_envio_em"] = None


def _rodar_em_thread(campanha_id, geracao):
    while True:
        # Parar + Retomar durante o intervalo cria uma thread nova enquanto a
        # antiga ainda dorme. Sem essa checagem, as duas acordariam enviando e o
        # intervalo real cairia pela metade - justamente o que queima o chip.
        if geracao != _geracao_thread:
            return
        resultado = processar_proximo(campanha_id)
        if resultado in ("concluida", "pausada_por_falhas", "nao_esta_rodando"):
            return
        if resultado in ESTADOS_QUE_ESPERAM:
            _dormir(60)
            continue
        if resultado == "pulado":
            continue  # nada foi enviado, não há por que esperar o intervalo

        conexao = db.conectar()
        try:
            linha = conexao.execute(
                "SELECT status, config_json FROM wa_campanhas WHERE id = ?", (campanha_id,)
            ).fetchone()
        finally:
            conexao.close()
        if not linha or linha["status"] != "rodando":
            return

        ritmo = {**RITMO_PADRAO, **(json.loads(linha["config_json"]).get("ritmo") or {})}
        _dormir_intervalo(campanha_id, ritmo)


def _iniciar_thread(campanha_id):
    global _thread_ativa, _geracao_thread
    with _lock_thread:
        _geracao_thread += 1
        _thread_ativa = threading.Thread(
            target=_rodar_em_thread, args=(campanha_id, _geracao_thread), daemon=True
        )
        _thread_ativa.start()
