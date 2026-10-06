"""Webhook da Evolution API: `messages.upsert` (mensagem entrando ou saindo)
e `connection.update` (mudança de estado da instância). A rota sempre responde
200 - qualquer falha aqui fica só no log, porque a Evolution reenvia o mesmo
evento indefinidamente até receber 2xx.

Regras do funil (INTEGRACAO.md):
- mensagem do lead → status 'respondeu' (nunca rebaixa: fechou/recusou/ignorado
  ficam como estão).
- mensagem do lead com texto de opt-out ("não tenho interesse", "sair", "pare",
  "remover") → status 'recusou' + `wa_optout = 1` (bloqueio permanente).
- mensagem enviada pelo próprio número (`fromMe`) fora do app (ex: o vendedor
  respondeu direto pelo celular) também vira registro 'vendedor' no cockpit -
  dedup pelo id da Evolution evita duplicar quando é eco do que o app mandou.
  Isso também pausa a resposta automática (`leads.wa_ia_pausada`), pra IA e o
  vendedor nunca responderem ao mesmo tempo.
- mensagem do lead (canal maps) aciona a resposta automática da IA
  (`whatsapp/autoresponder.py`), que conversa sozinha até o lead qualificar.
"""

import logging
import re
from datetime import datetime

import db
import rotas_conversa
from constantes import STATUS_QUE_ENCERRAM_FOLLOWUP

from . import autoresponder

logger = logging.getLogger(__name__)

# Frase inequívoca: vale em qualquer ponto da mensagem.
PADROES_OPTOUT = [
    re.compile(r"n[aã]o\s+tenho\s+interesse", re.IGNORECASE),
]

# Palavra solta é ambígua ("te chamo depois de sair da clínica"): só conta em
# mensagem curta, tipo "sair", "pare por favor", "me remover da lista". Um
# falso positivo aqui tira um lead quente da lista pra sempre.
PALAVRAS_OPTOUT = re.compile(r"\b(sair|pare|parem|remover|remova)\b", re.IGNORECASE)
MAX_PALAVRAS_OPTOUT_CURTO = 5


def _e_optout(texto_mensagem):
    bruto = (texto_mensagem or "").strip()
    if not bruto:
        return False
    if any(padrao.search(bruto) for padrao in PADROES_OPTOUT):
        return True
    return len(bruto.split()) <= MAX_PALAVRAS_OPTOUT_CURTO and bool(PALAVRAS_OPTOUT.search(bruto))


def _texto_da_mensagem(msg):
    if not isinstance(msg, dict):
        return ""
    if msg.get("conversation"):
        return str(msg["conversation"])
    estendida = msg.get("extendedTextMessage") or {}
    if estendida.get("text"):
        return str(estendida["text"])
    imagem = msg.get("imageMessage") or {}
    if imagem.get("caption"):
        return str(imagem["caption"])
    return ""


def _telefone_do_jid(remote_jid):
    bruto = str(remote_jid or "").split("@")[0]
    return re.sub(r"\D", "", bruto)


def _timestamp_para_iso(bruto):
    try:
        return datetime.fromtimestamp(int(bruto)).isoformat(timespec="seconds")
    except (TypeError, ValueError, OSError, OverflowError):
        return datetime.now().isoformat(timespec="seconds")


def _tratar_resposta_do_lead(canal, lead_ref, texto_mensagem):
    """Avança o funil pra 'respondeu' - ou pra 'recusou' + wa_optout=1 se for
    opt-out. Nunca mexe em status terminal (fechou/recusou/ignorado) e nunca
    repete a mesma transição."""
    if canal != "maps":
        return  # wa_optout e o funil automático são só do canal maps

    agora = datetime.now().isoformat(timespec="seconds")
    optout = _e_optout(texto_mensagem)

    conexao = db.conectar()
    try:
        lead = conexao.execute("SELECT status FROM leads WHERE place_id = ?", (lead_ref,)).fetchone()
        if not lead:
            return
        status_atual = lead["status"]

        if optout:
            conexao.execute("UPDATE leads SET wa_optout = 1 WHERE place_id = ?", (lead_ref,))
            if status_atual not in STATUS_QUE_ENCERRAM_FOLLOWUP:
                conexao.execute(
                    "UPDATE leads SET status = 'recusou', proximo_followup = NULL, atualizado_em = ? "
                    "WHERE place_id = ?",
                    (agora, lead_ref),
                )
                conexao.execute(
                    "INSERT INTO historico_status (place_id, status_anterior, status_novo, alterado_em) "
                    "VALUES (?, ?, 'recusou', ?)",
                    (lead_ref, status_atual, agora),
                )
            conexao.commit()
            return

        if status_atual in STATUS_QUE_ENCERRAM_FOLLOWUP or status_atual == "respondeu":
            return  # nunca rebaixa, nunca repete a mesma transição

        conexao.execute(
            "UPDATE leads SET status = 'respondeu', atualizado_em = ? WHERE place_id = ?",
            (agora, lead_ref),
        )
        conexao.execute(
            "INSERT INTO historico_status (place_id, status_anterior, status_novo, alterado_em) "
            "VALUES (?, ?, 'respondeu', ?)",
            (lead_ref, status_atual, agora),
        )
        conexao.commit()
    finally:
        conexao.close()


def _pausar_ia_por_intervencao_manual(lead_ref):
    """O vendedor respondeu direto pelo celular, fora do app: pausa a
    resposta automática pra sempre, pra IA nunca responder por cima dele."""
    conexao = db.conectar()
    try:
        conexao.execute("UPDATE leads SET wa_ia_pausada = 1 WHERE place_id = ?", (lead_ref,))
        conexao.commit()
    finally:
        conexao.close()


def _processar_mensagem_upsert(item):
    key = item.get("key") or {}
    remote_jid = key.get("remoteJid")
    from_me = bool(key.get("fromMe"))
    id_externo = key.get("id")
    texto_mensagem = _texto_da_mensagem(item.get("message"))
    if not texto_mensagem or not remote_jid:
        return

    telefone = _telefone_do_jid(remote_jid)
    if not telefone:
        return

    canal, lead_ref = rotas_conversa._resolver_lead_por_telefone(telefone)
    if not lead_ref:
        return  # número sem lead correspondente: mesma regra da ingestão passiva do cockpit

    enviada_em = _timestamp_para_iso(item.get("messageTimestamp"))
    autor = "vendedor" if from_me else "lead"
    chave = rotas_conversa._chave_dedup(autor, texto_mensagem, enviada_em, id_externo)

    # origem é sempre "whatsapp" aqui - é o que o webhook captura de fora do
    # app. Quando o próprio app manda uma mensagem, a Evolution ecoa esse
    # envio de volta como fromMe=true com o MESMO id_externo: como a chave de
    # dedup usa esse id, o INSERT OR IGNORE nem chega a rodar (já existe uma
    # linha "app" com essa chave) - só sobra "whatsapp" pra quem realmente foi
    # mandado fora do app (ex: o vendedor respondeu direto pelo celular).
    conexao = db.conectar()
    try:
        gravou = rotas_conversa._inserir_mensagem(
            conexao, canal, lead_ref, autor, texto_mensagem, enviada_em, "whatsapp", chave,
        )
        conexao.commit()
    finally:
        conexao.close()

    if not gravou:
        return

    if from_me:
        if canal == "maps":
            _pausar_ia_por_intervencao_manual(lead_ref)
        return

    _tratar_resposta_do_lead(canal, lead_ref, texto_mensagem)
    if canal == "maps":
        autoresponder.processar_mensagem_recebida(lead_ref, telefone)


def _processar_connection_update(dados):
    """Só loga - `/api/whatsapp/estado` sempre consulta a Evolution na hora,
    não existe estado local pra sincronizar aqui."""
    estado = (dados or {}).get("state") or (dados or {}).get("connection")
    logger.info("webhook: conexão da instância mudou para %s", estado)


def processar_evento(payload):
    """Nunca lança: qualquer falha é logada e ignorada, pra rota sempre
    responder 200 (a Evolution re-tenta o mesmo evento até receber 2xx)."""
    if not isinstance(payload, dict):
        return
    evento = payload.get("event") or ""
    dados = payload.get("data")

    try:
        if evento == "messages.upsert":
            if isinstance(dados, list):
                itens = dados
            elif isinstance(dados, dict):
                itens = [dados]
            else:
                itens = []
            for item in itens:
                if isinstance(item, dict):
                    _processar_mensagem_upsert(item)
        elif evento == "connection.update":
            _processar_connection_update(dados)
    except Exception:
        logger.exception("falha ao processar evento do webhook da Evolution (%s)", evento)
