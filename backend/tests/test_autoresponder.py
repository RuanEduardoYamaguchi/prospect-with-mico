"""Testes da resposta automática por IA (whatsapp/autoresponder.py): a IA
responde sozinha até o lead qualificar (estágio 'negociacao'/'fechamento' na
leitura do analista de conversa), aí pausa pra sempre e avisa o responsável
pelo WhatsApp. IA e Evolution são sempre monkeypatch - sem rede, sem custo de
API real.
"""

import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import db
import processar
from whatsapp import autoresponder, evolution, schema


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
    # o padrão é desligada; os testes daqui exercitam a resposta ligada
    db.salvar_config("wa_autoresposta_ativa", "1")
    return caminho


def criar_lead(place_id="place-1", telefone="11999990001", status="respondeu",
               wa_ia_pausada=0, wa_optout=0):
    conexao = db.conectar()
    try:
        conexao.execute(
            "INSERT INTO leads (place_id, nome, categoria, endereco, nota, num_avaliacoes, "
            "telefone, whatsapp_link, site_status, status, wa_ia_pausada, wa_optout, "
            "visto_em, atualizado_em) "
            "VALUES (?, 'Clínica Sorriso', 'Clínica', 'Rua X', 4.8, 90, ?, ?, 'sem_site', ?, ?, ?, "
            "'2026-09-01', '2026-09-01')",
            (place_id, telefone, f"https://wa.me/55{telefone}", status, wa_ia_pausada, wa_optout),
        )
        conexao.execute(
            "INSERT INTO mensagens_conversa (canal, lead_ref, autor, texto, enviada_em, origem, "
            "chave_dedup, criada_em) VALUES "
            "('maps', ?, 'lead', 'Quanto custa o site?', '2026-09-21T10:00:00', 'whatsapp', 'h:1', "
            "'2026-09-21T10:00:00')",
            (place_id,),
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


def mensagens_do_lead(place_id):
    conexao = db.conectar()
    try:
        linhas = conexao.execute(
            "SELECT autor, texto, origem FROM mensagens_conversa WHERE canal='maps' AND lead_ref=? ORDER BY id",
            (place_id,),
        ).fetchall()
    finally:
        conexao.close()
    return [dict(l) for l in linhas]


def _analise(estagio, resposta_sugerida="oi, tudo bem? posso te mandar uma prévia"):
    return {
        "estagio": estagio,
        "leitura": "o lead perguntou o preço, sinal de interesse real",
        "objetivo": "responder a pergunta",
        "resposta_sugerida": resposta_sugerida,
        "evitar": [],
    }


@pytest.fixture
def evolution_fake(monkeypatch):
    estado = {"conectado": True}
    enviados = []

    def _estado():
        return {"conectado": estado["conectado"]}

    def _enviar_texto(numero, texto):
        enviados.append((numero, texto))
        return {"key": {"id": f"evo-{len(enviados)}"}}

    monkeypatch.setattr(autoresponder.evolution, "estado", _estado)
    monkeypatch.setattr(autoresponder.evolution, "enviar_texto", _enviar_texto)
    return estado, enviados


# ---------------------------------------------------------------------------
# Ainda não qualificou: responde sozinha
# ---------------------------------------------------------------------------

class TestRespostaAutomatica:
    def test_responde_o_lead_quando_ainda_nao_qualificou(self, banco, monkeypatch, evolution_fake):
        _estado, enviados = evolution_fake
        monkeypatch.setattr(
            autoresponder.ia, "analisar_conversa_com_fallback",
            lambda lead, mensagens: (_analise("descoberta"), "anthropic", []),
        )
        criar_lead()

        autoresponder.processar_mensagem_recebida("place-1", "11999990001")

        assert enviados == [("5511999990001", "oi, tudo bem? posso te mandar uma prévia")]
        assert obter_lead("place-1")["wa_ia_pausada"] == 0
        mensagens = mensagens_do_lead("place-1")
        assert mensagens[-1]["autor"] == "vendedor"
        assert mensagens[-1]["origem"] == "app"

    def test_sem_resposta_sugerida_nao_manda_nada(self, banco, monkeypatch, evolution_fake):
        _estado, enviados = evolution_fake
        monkeypatch.setattr(
            autoresponder.ia, "analisar_conversa_com_fallback",
            lambda lead, mensagens: (_analise("descoberta", resposta_sugerida=""), "anthropic", []),
        )
        criar_lead()
        autoresponder.processar_mensagem_recebida("place-1", "11999990001")
        assert enviados == []


# ---------------------------------------------------------------------------
# Qualificou: pausa pra sempre e avisa o responsável, sem responder o lead
# ---------------------------------------------------------------------------

class TestQualificacao:
    @pytest.mark.parametrize("estagio", ["negociacao", "fechamento"])
    def test_qualificou_pausa_e_avisa_sem_responder_o_lead(self, banco, monkeypatch, evolution_fake, estagio):
        _estado, enviados = evolution_fake
        monkeypatch.setenv("NUMERO_NOTIFICACAO_QUALIFICACAO", "11988887777")
        monkeypatch.setattr(
            autoresponder.ia, "analisar_conversa_com_fallback",
            lambda lead, mensagens: (_analise(estagio), "anthropic", []),
        )
        criar_lead()

        autoresponder.processar_mensagem_recebida("place-1", "11999990001")

        assert obter_lead("place-1")["wa_ia_pausada"] == 1
        assert len(enviados) == 1
        numero, texto = enviados[0]
        assert numero == "5511988887777"
        assert "Clínica Sorriso" in texto
        # nada novo gravado como vendedor/app - só a notificação pro responsável
        assert all(m["autor"] != "vendedor" for m in mensagens_do_lead("place-1"))

    def test_sem_numero_de_notificacao_pausa_mas_nao_avisa_ninguem(self, banco, monkeypatch, evolution_fake):
        _estado, enviados = evolution_fake
        monkeypatch.delenv("NUMERO_NOTIFICACAO_QUALIFICACAO", raising=False)
        monkeypatch.setattr(
            autoresponder.ia, "analisar_conversa_com_fallback",
            lambda lead, mensagens: (_analise("negociacao"), "anthropic", []),
        )
        criar_lead()

        autoresponder.processar_mensagem_recebida("place-1", "11999990001")

        assert obter_lead("place-1")["wa_ia_pausada"] == 1
        assert enviados == []

    def test_numero_de_notificacao_configuravel_por_env(self, banco, monkeypatch, evolution_fake):
        _estado, enviados = evolution_fake
        monkeypatch.setenv("NUMERO_NOTIFICACAO_QUALIFICACAO", "11988887777")
        monkeypatch.setattr(
            autoresponder.ia, "analisar_conversa_com_fallback",
            lambda lead, mensagens: (_analise("negociacao"), "anthropic", []),
        )
        criar_lead()
        autoresponder.processar_mensagem_recebida("place-1", "11999990001")
        assert enviados[0][0] == "5511988887777"


# ---------------------------------------------------------------------------
# Travas: nunca chama IA/Evolution fora da hora
# ---------------------------------------------------------------------------

class TestTravas:
    def test_ia_pausada_nao_chama_ia_nem_evolution(self, banco, monkeypatch, evolution_fake):
        _estado, enviados = evolution_fake
        chamou_ia = []
        monkeypatch.setattr(
            autoresponder.ia, "analisar_conversa_com_fallback",
            lambda lead, mensagens: chamou_ia.append(True) or (_analise("descoberta"), "anthropic", []),
        )
        criar_lead(wa_ia_pausada=1)

        autoresponder.processar_mensagem_recebida("place-1", "11999990001")

        assert chamou_ia == []
        assert enviados == []

    def test_optout_nao_chama_ia_nem_evolution(self, banco, monkeypatch, evolution_fake):
        _estado, enviados = evolution_fake
        chamou_ia = []
        monkeypatch.setattr(
            autoresponder.ia, "analisar_conversa_com_fallback",
            lambda lead, mensagens: chamou_ia.append(True) or (_analise("descoberta"), "anthropic", []),
        )
        criar_lead(wa_optout=1)

        autoresponder.processar_mensagem_recebida("place-1", "11999990001")

        assert chamou_ia == []
        assert enviados == []

    def test_whatsapp_desconectado_nao_chama_ia(self, banco, monkeypatch, evolution_fake):
        estado, enviados = evolution_fake
        estado["conectado"] = False
        chamou_ia = []
        monkeypatch.setattr(
            autoresponder.ia, "analisar_conversa_com_fallback",
            lambda lead, mensagens: chamou_ia.append(True) or (_analise("descoberta"), "anthropic", []),
        )
        criar_lead()

        autoresponder.processar_mensagem_recebida("place-1", "11999990001")

        assert chamou_ia == []
        assert enviados == []

    def test_autoresposta_desligada_nao_chama_ia_nem_envia_nem_pausa(self, banco, monkeypatch, evolution_fake):
        _estado, enviados = evolution_fake
        chamou_ia = []
        monkeypatch.setattr(
            autoresponder.ia, "analisar_conversa_com_fallback",
            lambda lead, mensagens: chamou_ia.append(True) or (_analise("negociacao"), "anthropic", []),
        )
        db.salvar_config("wa_autoresposta_ativa", "0")
        criar_lead()

        autoresponder.processar_mensagem_recebida("place-1", "11999990001")

        assert chamou_ia == []
        assert enviados == []
        assert obter_lead("place-1")["wa_ia_pausada"] == 0

    def test_desligar_durante_a_analise_da_ia_nao_envia(self, banco, monkeypatch, evolution_fake):
        _estado, enviados = evolution_fake

        def _analise_que_desliga(lead, mensagens):
            db.salvar_config("wa_autoresposta_ativa", "0")
            return _analise("descoberta"), "anthropic", []

        monkeypatch.setattr(autoresponder.ia, "analisar_conversa_com_fallback", _analise_que_desliga)
        criar_lead()

        autoresponder.processar_mensagem_recebida("place-1", "11999990001")

        assert enviados == []
        assert [m["autor"] for m in mensagens_do_lead("place-1")] == ["lead"]

    def test_lead_inexistente_nao_lanca(self, banco, evolution_fake):
        autoresponder.processar_mensagem_recebida("place-fantasma", "11999990001")


# ---------------------------------------------------------------------------
# Robustez: falhas nunca vazam pro webhook que chama isto
# ---------------------------------------------------------------------------

class TestRobustez:
    def test_nenhum_provedor_de_ia_nao_lanca(self, banco, evolution_fake, monkeypatch):
        def _levanta(lead, mensagens):
            raise autoresponder.ia.NenhumProvedorDisponivel(None)

        monkeypatch.setattr(autoresponder.ia, "analisar_conversa_com_fallback", _levanta)
        criar_lead()
        autoresponder.processar_mensagem_recebida("place-1", "11999990001")

    def test_falha_ao_enviar_resposta_nao_lanca_e_registra_falha(self, banco, monkeypatch, evolution_fake):
        def _falha(numero, texto):
            raise evolution.ErroEvolution("Evolution respondeu 500")

        monkeypatch.setattr(autoresponder.evolution, "enviar_texto", _falha)
        monkeypatch.setattr(
            autoresponder.ia, "analisar_conversa_com_fallback",
            lambda lead, mensagens: (_analise("descoberta"), "anthropic", []),
        )
        criar_lead()
        autoresponder.processar_mensagem_recebida("place-1", "11999990001")

        conexao = db.conectar()
        try:
            envio = conexao.execute(
                "SELECT status FROM wa_envios WHERE place_id = ?", ("place-1",)
            ).fetchone()
        finally:
            conexao.close()
        assert envio["status"] == "falhou"
