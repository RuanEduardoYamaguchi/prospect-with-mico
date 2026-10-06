"""Testes do motor de campanha (whatsapp/campanha.py): filtro de leads, teto do
aquecimento, janela de horário, 5 falhas seguidas, sobrevivência a restart e os
efeitos colaterais de um envio (status do lead, follow-up, cockpit de conversa).

Evolution é sempre um fake em memória (sem rede) e `_dormir`/`_agora`/
`_aleatorio` são monkeypatchados pra rodar tudo instantâneo e determinístico -
`processar_proximo()` é chamado direto, sem thread.
"""

import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import db
import processar
from whatsapp import aquecimento, campanha, schema


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

class EvolutionFake:
    """Substitui whatsapp.evolution nos testes: nunca toca rede."""

    def __init__(self):
        self.conectado = True
        self.numeros_sem_whatsapp = set()
        self.numeros_que_falham = set()
        self.enviados = []

    def estado(self):
        return {
            "evolution_ok": True,
            "conectado": self.conectado,
            "estado": "open" if self.conectado else "close",
            "numero": "5541999990000" if self.conectado else None,
            "instancia": "prospector",
        }

    def numeros_com_whatsapp(self, numeros):
        return {n: {"existe": n not in self.numeros_sem_whatsapp, "jid": f"{n}@s.whatsapp.net"} for n in numeros}

    def enviar_texto(self, numero, texto):
        if numero in self.numeros_que_falham:
            raise Exception("Evolution respondeu 500")
        self.enviados.append((numero, texto))
        return {"key": {"id": f"id-{len(self.enviados)}"}}


@pytest.fixture
def banco(tmp_path, monkeypatch):
    caminho = tmp_path / "leads_teste.db"
    monkeypatch.setattr(db, "CAMINHO_BANCO", caminho)
    conexao = sqlite3.connect(caminho)
    try:
        processar.preparar_banco(conexao)
        schema.preparar(conexao)
    finally:
        conexao.close()
    return caminho


AGORA_DENTRO_DA_JANELA = datetime(2026, 9, 21, 10, 0, 0)  # segunda, 10h - dentro de 09h-18h
AGORA_FORA_DA_JANELA = datetime(2026, 9, 21, 22, 0, 0)  # 22h - fora de 09h-18h


@pytest.fixture
def motor(banco, monkeypatch):
    """Injeta as dependências do motor: evolution fake, sleep no-op, relógio
    fixo dentro da janela comercial e sorteio determinístico (sempre a
    primeira opção do spintax). `_iniciar_thread` também vira no-op: os testes
    dirigem o motor chamando `processar_proximo`/`rodar_ate_terminar` na mão,
    senão a thread real (com sleep zerado) correria sozinha e em paralelo com
    o teste, causando corrida."""
    fake = EvolutionFake()
    monkeypatch.setattr(campanha, "_evolution", fake)
    monkeypatch.setattr(campanha, "_dormir", lambda segundos: None)
    monkeypatch.setattr(campanha, "_agora", lambda: AGORA_DENTRO_DA_JANELA)
    monkeypatch.setattr(campanha, "_aleatorio", lambda: 0.0)
    monkeypatch.setattr(campanha, "_iniciar_thread", lambda campanha_id: None)
    campanha._estado_ao_vivo.clear()
    return fake


def criar_lead(place_id="place-1", nome="Clínica Sorriso", telefone="11999990001",
                 nota=4.8, num_avaliacoes=90, site_status="sem_site", status="novo",
                 nicho="odontologia", cidade="Londrina"):
    conexao = db.conectar()
    try:
        conexao.execute(
            "INSERT INTO leads (place_id, nome, categoria, endereco, nota, num_avaliacoes, "
            "telefone, whatsapp_link, site_status, nicho, cidade, status, visto_em, atualizado_em) "
            "VALUES (?, ?, 'Clínica', 'Rua X', ?, ?, ?, ?, ?, ?, ?, ?, '2026-09-01', '2026-09-01')",
            (place_id, nome, nota, num_avaliacoes, telefone, f"https://wa.me/55{telefone}",
             site_status, nicho, cidade, status),
        )
        conexao.commit()
    finally:
        conexao.close()
    return place_id


def obter_lead(place_id):
    conexao = db.conectar()
    try:
        linha = conexao.execute("SELECT * FROM leads WHERE place_id = ?", (place_id,)).fetchone()
    finally:
        conexao.close()
    return dict(linha) if linha else None


def rodar_ate_terminar(campanha_id, limite_passos=200):
    """Roda processar_proximo em loop até a campanha sair do estado 'rodando'
    ou até o teto de segurança - evita loop infinito num teste com bug."""
    resultados = []
    for _ in range(limite_passos):
        resultado = campanha.processar_proximo(campanha_id)
        resultados.append(resultado)
        if resultado in ("concluida", "pausada_por_falhas", "nao_esta_rodando"):
            break
    return resultados


# ---------------------------------------------------------------------------
# Filtro de leads / prévia
# ---------------------------------------------------------------------------

class TestFiltroDeLeads:
    def test_previa_traz_leads_que_batem_com_o_filtro(self, banco, monkeypatch):
        monkeypatch.setattr(aquecimento, "restantes_hoje", lambda: 15)
        criar_lead(place_id="a", nicho="odontologia", nota=4.8, num_avaliacoes=90)
        criar_lead(place_id="b", nicho="estética", nota=4.8, num_avaliacoes=90)

        resultado = campanha.previa({"nicho": "odontologia"}, "Oi {{nome}}", None)
        assert resultado["total"] == 1
        assert resultado["leads"][0]["place_id"] == "a"

    def test_so_celular_descarta_fixo(self, banco, monkeypatch):
        monkeypatch.setattr(aquecimento, "restantes_hoje", lambda: 15)
        criar_lead(place_id="celular", telefone="11999990001")
        criar_lead(place_id="fixo", telefone="6533221122")

        resultado = campanha.previa({"so_celular": True}, "Oi", None)
        assert [l["place_id"] for l in resultado["leads"]] == ["celular"]
        assert resultado["descartados"].get("telefone fixo") == 1

    def test_score_min_e_max_filtram(self, banco, monkeypatch):
        monkeypatch.setattr(aquecimento, "restantes_hoje", lambda: 15)
        criar_lead(place_id="baixo", nota=4.0, num_avaliacoes=0, site_status="site_ok")
        criar_lead(place_id="medio", nota=4.5, num_avaliacoes=20, site_status="sem_site")

        resultado = campanha.previa({"score_min": 40, "score_max": 69}, "Oi", None)
        ids = [l["place_id"] for l in resultado["leads"]]
        assert "medio" in ids
        assert "baixo" not in ids

    def test_pular_contatados_remove_quem_ja_recebeu(self, banco, monkeypatch):
        monkeypatch.setattr(aquecimento, "restantes_hoje", lambda: 15)
        criar_lead(place_id="ja-mandou", telefone="11999990001")
        conexao = db.conectar()
        try:
            conexao.execute(
                "INSERT INTO wa_envios (place_id, telefone, texto, status, enviado_em) "
                "VALUES ('ja-mandou', '5511999990001', 'oi', 'enviado', '2026-09-01T10:00:00')"
            )
            conexao.commit()
        finally:
            conexao.close()

        resultado = campanha.previa({"pular_contatados": True}, "Oi", None)
        assert resultado["leads"] == []
        assert resultado["descartados"].get("já recebeu mensagem antes") == 1

    def test_aviso_quando_lista_maior_que_teto(self, banco, monkeypatch):
        monkeypatch.setattr(aquecimento, "restantes_hoje", lambda: 1)
        criar_lead(place_id="a", telefone="11999990001")
        criar_lead(place_id="b", telefone="11999990002")

        resultado = campanha.previa({}, "Oi", None)
        assert resultado["total"] == 2
        assert resultado["teto_restante"] == 1
        assert resultado["aviso"] is not None

    def test_limite_corta_a_lista(self, banco, monkeypatch):
        monkeypatch.setattr(aquecimento, "restantes_hoje", lambda: 15)
        for i in range(5):
            criar_lead(place_id=f"lead-{i}", telefone=f"1199999000{i}")
        resultado = campanha.previa({}, "Oi", 2)
        assert resultado["total"] == 2

    def test_texto_exemplo_usa_variaveis_do_lead(self, banco, monkeypatch):
        monkeypatch.setattr(aquecimento, "restantes_hoje", lambda: 15)
        criar_lead(place_id="a", nome="Clínica Sorriso")
        resultado = campanha.previa({}, "Oi {{nome}}!", None)
        assert resultado["leads"][0]["texto_exemplo"] == "Oi Clínica Sorriso!"


# ---------------------------------------------------------------------------
# Envio bem-sucedido: efeitos colaterais
# ---------------------------------------------------------------------------

class TestEnvioBemSucedido:
    def test_envio_marca_contatado_e_followup_e_grava_conversa(self, motor, banco):
        criar_lead(place_id="p1", status="novo")
        nova = campanha.criar_campanha("Teste", {}, "Oi {{nome}}!", None, None, checar_whatsapp=False)

        resultado = campanha.processar_proximo(nova["id"])
        assert resultado == "enviado"

        lead = obter_lead("p1")
        assert lead["status"] == "contatado"
        assert lead["proximo_followup"] == (AGORA_DENTRO_DA_JANELA.date() + timedelta(days=3)).isoformat()

        conexao = db.conectar()
        try:
            mensagens = conexao.execute(
                "SELECT autor, origem, texto FROM mensagens_conversa WHERE canal='maps' AND lead_ref='p1'"
            ).fetchall()
        finally:
            conexao.close()
        assert len(mensagens) == 1
        assert mensagens[0]["autor"] == "vendedor"
        assert mensagens[0]["origem"] == "app"

    def test_envio_nunca_rebaixa_status_ja_avancado(self, motor, banco):
        criar_lead(place_id="p1", status="respondeu")
        nova = campanha.criar_campanha(
            "Teste", {"status": ["respondeu"]}, "Oi {{nome}}!", None, None, checar_whatsapp=False
        )
        campanha.processar_proximo(nova["id"])
        assert obter_lead("p1")["status"] == "respondeu"  # não voltou pra 'contatado'

    def test_campanha_atualiza_contadores(self, motor, banco):
        criar_lead(place_id="p1")
        nova = campanha.criar_campanha("Teste", {}, "Oi!", None, None, checar_whatsapp=False)
        campanha.processar_proximo(nova["id"])
        atualizada = campanha.obter_campanha(nova["id"])
        assert atualizada["enviados"] == 1
        assert atualizada["status"] == "rodando"

    def test_fila_esgotada_conclui_campanha(self, motor, banco):
        criar_lead(place_id="p1")
        nova = campanha.criar_campanha("Teste", {}, "Oi!", None, None, checar_whatsapp=False)
        resultados = rodar_ate_terminar(nova["id"])
        assert resultados[-1] == "concluida"
        assert campanha.obter_campanha(nova["id"])["status"] == "concluida"


# ---------------------------------------------------------------------------
# Teto do aquecimento
# ---------------------------------------------------------------------------

class TestTetoDoAquecimento:
    def test_teto_esgotado_espera_em_vez_de_falhar(self, motor, banco, monkeypatch):
        criar_lead(place_id="p1")
        nova = campanha.criar_campanha("Teste", {}, "Oi!", None, None, checar_whatsapp=False)
        monkeypatch.setattr(aquecimento, "restantes_hoje", lambda: 0)

        resultado = campanha.processar_proximo(nova["id"])
        assert resultado == "aguardando_teto"
        assert motor.enviados == []
        assert campanha.obter_campanha(nova["id"])["status"] == "rodando"


# ---------------------------------------------------------------------------
# Janela de horário
# ---------------------------------------------------------------------------

class TestJanelaDeHorario:
    def test_fora_da_janela_espera_em_vez_de_falhar(self, motor, banco, monkeypatch):
        criar_lead(place_id="p1")
        nova = campanha.criar_campanha("Teste", {}, "Oi!", None, None, checar_whatsapp=False)
        monkeypatch.setattr(campanha, "_agora", lambda: AGORA_FORA_DA_JANELA)

        resultado = campanha.processar_proximo(nova["id"])
        assert resultado == "aguardando_janela"
        assert motor.enviados == []

    def test_volta_a_enviar_quando_a_janela_abre(self, motor, banco, monkeypatch):
        criar_lead(place_id="p1")
        nova = campanha.criar_campanha("Teste", {}, "Oi!", None, None, checar_whatsapp=False)
        monkeypatch.setattr(campanha, "_agora", lambda: AGORA_FORA_DA_JANELA)
        assert campanha.processar_proximo(nova["id"]) == "aguardando_janela"

        monkeypatch.setattr(campanha, "_agora", lambda: AGORA_DENTRO_DA_JANELA)
        assert campanha.processar_proximo(nova["id"]) == "enviado"


# ---------------------------------------------------------------------------
# WhatsApp desconectado
# ---------------------------------------------------------------------------

class TestConexao:
    def test_desconectado_espera_em_vez_de_falhar(self, motor, banco):
        criar_lead(place_id="p1")
        nova = campanha.criar_campanha("Teste", {}, "Oi!", None, None, checar_whatsapp=False)
        motor.conectado = False

        resultado = campanha.processar_proximo(nova["id"])
        assert resultado == "aguardando_conexao"
        assert motor.enviados == []


# ---------------------------------------------------------------------------
# Checagem de número com WhatsApp
# ---------------------------------------------------------------------------

class TestChecarWhatsapp:
    def test_numero_sem_whatsapp_e_pulado(self, motor, banco):
        criar_lead(place_id="p1", telefone="11999990001")
        motor.numeros_sem_whatsapp.add("5511999990001")
        nova = campanha.criar_campanha("Teste", {}, "Oi!", None, None, checar_whatsapp=True)

        resultado = campanha.processar_proximo(nova["id"])
        assert resultado == "pulado"
        assert motor.enviados == []
        assert campanha.obter_campanha(nova["id"])["pulados"] == 1


# ---------------------------------------------------------------------------
# 5 falhas seguidas
# ---------------------------------------------------------------------------

class TestFalhasSeguidas:
    def test_cinco_falhas_seguidas_pausa_a_campanha(self, motor, banco):
        for i in range(5):
            criar_lead(place_id=f"p{i}", telefone=f"1199999000{i}")
        motor.numeros_que_falham = {f"551199999000{i}" for i in range(5)}
        nova = campanha.criar_campanha("Teste", {}, "Oi!", None, None, checar_whatsapp=False)

        resultados = rodar_ate_terminar(nova["id"])
        assert resultados[-1] == "pausada_por_falhas"

        atualizada = campanha.obter_campanha(nova["id"])
        assert atualizada["status"] == "pausada"
        assert atualizada["falhas"] == 5
        assert "Cinco falhas seguidas" in atualizada["ultimo_erro"]

    def test_uma_falha_isolada_nao_pausa(self, motor, banco):
        criar_lead(place_id="p1", telefone="11999990001")
        criar_lead(place_id="p2", telefone="11999990002")
        motor.numeros_que_falham = {"5511999990001"}
        nova = campanha.criar_campanha("Teste", {}, "Oi!", None, None, checar_whatsapp=False)

        resultados = rodar_ate_terminar(nova["id"])
        assert "falhou" in resultados
        assert resultados[-1] == "concluida"


# ---------------------------------------------------------------------------
# Restart: rodando -> interrompida -> retomar sem reenviar
# ---------------------------------------------------------------------------

class TestRestart:
    def test_restart_marca_interrompida_e_retomar_nao_reenvia(self, motor, banco):
        criar_lead(place_id="p1")
        criar_lead(place_id="p2", telefone="11999990002")
        nova = campanha.criar_campanha("Teste", {}, "Oi!", None, None, checar_whatsapp=False)

        # envia o primeiro, simula o backend caindo no meio
        assert campanha.processar_proximo(nova["id"]) == "enviado"
        campanha.marcar_campanhas_interrompidas()
        assert campanha.obter_campanha(nova["id"])["status"] == "interrompida"

        # ninguém foi reenviado nem re-sofreu efeito colateral
        assert len(motor.enviados) == 1

        resultado, erro = campanha.retomar(nova["id"])
        assert erro is None
        assert resultado["status"] == "rodando"

        resultados = rodar_ate_terminar(nova["id"])
        assert resultados[-1] == "concluida"
        assert len(motor.enviados) == 2  # só o segundo lead, o primeiro não repetiu
        numeros_enviados = [n for n, _ in motor.enviados]
        assert len(numeros_enviados) == len(set(numeros_enviados))  # nenhum duplicado


# ---------------------------------------------------------------------------
# Parar / descartar
# ---------------------------------------------------------------------------

class TestPararEDescartar:
    def test_parar_pausa_a_campanha(self, motor, banco):
        criar_lead(place_id="p1")
        nova = campanha.criar_campanha("Teste", {}, "Oi!", None, None, checar_whatsapp=False)
        resultado, erro = campanha.parar(nova["id"])
        assert erro is None
        assert resultado["status"] == "pausada"
        assert campanha.processar_proximo(nova["id"]) == "nao_esta_rodando"

    def test_descartar_marca_pendentes_como_pulados(self, motor, banco):
        criar_lead(place_id="p1")
        criar_lead(place_id="p2", telefone="11999990002")
        nova = campanha.criar_campanha("Teste", {}, "Oi!", None, None, checar_whatsapp=False)
        resultado, erro = campanha.descartar(nova["id"])
        assert erro is None
        assert resultado["status"] == "parada"
        assert resultado["pulados"] == 2
        assert resultado["finalizada_em"] is not None

    def test_retomar_campanha_inexistente_da_erro(self, banco):
        resultado, erro = campanha.retomar(999)
        assert resultado is None
        assert "não encontrada" in erro


# ---------------------------------------------------------------------------
# Parar + Retomar no meio do intervalo não pode deixar duas threads enviando
# ---------------------------------------------------------------------------

def test_thread_de_geracao_antiga_sai_sem_enviar(monkeypatch):
    chamadas = []
    monkeypatch.setattr(campanha, "processar_proximo", lambda cid: chamadas.append(cid) or "concluida")
    monkeypatch.setattr(campanha, "_geracao_thread", 2)

    campanha._rodar_em_thread(1, geracao=1)  # thread antiga acordando depois do Retomar
    assert chamadas == []

    campanha._rodar_em_thread(1, geracao=2)  # a thread atual segue normal
    assert chamadas == [1]


def test_pulado_nao_espera_o_intervalo(monkeypatch):
    resultados = iter(["pulado", "pulado", "concluida"])
    monkeypatch.setattr(campanha, "processar_proximo", lambda cid: next(resultados))
    monkeypatch.setattr(campanha, "_geracao_thread", 1)
    esperas = []
    monkeypatch.setattr(campanha, "_dormir_intervalo", lambda cid, ritmo: esperas.append(cid))

    campanha._rodar_em_thread(1, geracao=1)
    assert esperas == []


# ---------------------------------------------------------------------------
# Número oficial (NUMERO_OFICIAL) nunca faz disparo
# ---------------------------------------------------------------------------

def test_campanha_pausa_se_o_numero_conectado_for_o_oficial(motor, banco, monkeypatch):
    criar_lead()
    nova = campanha.criar_campanha("Teste", {}, "Oi!", None, None, checar_whatsapp=False)
    estado_real = motor.estado
    monkeypatch.setattr(motor, "estado", lambda: {**estado_real(), "numero_oficial": True})

    assert campanha.processar_proximo(nova["id"]) == "pausada_por_falhas"
    assert motor.enviados == []
    assert campanha.obter_campanha(nova["id"])["status"] == "pausada"


def test_reconhece_o_numero_oficial(monkeypatch):
    from whatsapp import evolution
    monkeypatch.setenv("NUMERO_OFICIAL", "41 98888-7777")
    assert evolution.e_numero_oficial("5541988887777")
    assert evolution.e_numero_oficial("+55 41 98888-7777")
    assert evolution.e_numero_oficial("554188887777")  # WhatsApp às vezes omite o nono dígito
    assert not evolution.e_numero_oficial("5541999990000")
    assert not evolution.e_numero_oficial(None)


def test_sem_numero_oficial_configurado_a_trava_fica_desligada(monkeypatch):
    from whatsapp import evolution
    monkeypatch.delenv("NUMERO_OFICIAL", raising=False)
    assert not evolution.e_numero_oficial("5541988887777")


def test_liberar_campanha_no_oficial_derruba_o_teto_pra_20(banco, monkeypatch):
    from whatsapp import evolution
    monkeypatch.setenv("PERMITIR_CAMPANHA_NO_OFICIAL", "true")
    monkeypatch.delenv("TETO_NUMERO_OFICIAL", raising=False)
    assert evolution.campanha_no_oficial_liberada()
    assert aquecimento.resumo()["teto_hoje"] == min(aquecimento.TETO_INICIAL, aquecimento.TETO_NUMERO_OFICIAL)

    # mesmo com o chip "maduro" (teto do aquecimento acima de 20), fica em 20
    monkeypatch.setattr(aquecimento, "teto_do_dia", lambda dia: 150)
    assert aquecimento.resumo()["teto_hoje"] == 20


def test_teto_do_oficial_zerado_no_env_vale_so_o_aquecimento(banco, monkeypatch):
    monkeypatch.setenv("PERMITIR_CAMPANHA_NO_OFICIAL", "true")
    monkeypatch.setenv("TETO_NUMERO_OFICIAL", "0")
    monkeypatch.setattr(aquecimento, "teto_do_dia", lambda dia: 150)
    assert aquecimento.resumo()["teto_hoje"] == 150


def test_sem_liberacao_o_oficial_continua_bloqueado(monkeypatch):
    from whatsapp import evolution
    monkeypatch.delenv("PERMITIR_CAMPANHA_NO_OFICIAL", raising=False)
    assert not evolution.campanha_no_oficial_liberada()


def test_numero_oficial_com_sufixo_de_aparelho(monkeypatch):
    from whatsapp import evolution
    monkeypatch.setenv("NUMERO_OFICIAL", "41988887777")
    assert evolution.e_numero_oficial("5541988887777:12@s.whatsapp.net")


def test_numero_oficial_invalido_avisa_no_log(monkeypatch, caplog):
    from whatsapp import evolution
    monkeypatch.setenv("NUMERO_OFICIAL", "9999-0000")
    assert not evolution.e_numero_oficial("5541988887777")
    assert "DESLIGADA" in caplog.text
