"""Testes do webhook da Evolution (whatsapp/webhook.py): mensagem do lead
avança pra 'respondeu', opt-out avança pra 'recusou' + wa_optout=1, mensagem
fromMe fora do app vira registro 'vendedor', e nada disso nunca rebaixa um
status que já avançou mais. Tudo local, sem rede - o "payload" é só um dict
Python, do jeito que a Evolution manda pro webhook.
"""

import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import db
import processar
import rotas_conversa
from whatsapp import schema, webhook
from whatsapp import autoresponder as autoresponder_modulo


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


@pytest.fixture(autouse=True)
def limpar_lead_ativo():
    rotas_conversa._lead_ativo.update({"canal": None, "lead_ref": None, "telefone": None, "nome": None})
    yield


def criar_lead(place_id="place-1", telefone="11999990001", status="novo"):
    conexao = db.conectar()
    try:
        conexao.execute(
            "INSERT INTO leads (place_id, nome, categoria, endereco, nota, num_avaliacoes, "
            "telefone, whatsapp_link, site_status, status, visto_em, atualizado_em) "
            "VALUES (?, 'Clínica Sorriso', 'Clínica', 'Rua X', 4.8, 90, ?, ?, 'sem_site', ?, "
            "'2026-09-01', '2026-09-01')",
            (place_id, telefone, f"https://wa.me/55{telefone}", status),
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


def evento_upsert(remote_jid, texto, from_me=False, id_externo="msg-1", timestamp=1758445200):
    return {
        "event": "messages.upsert",
        "instance": "prospector",
        "data": {
            "key": {"remoteJid": remote_jid, "fromMe": from_me, "id": id_externo},
            "message": {"conversation": texto},
            "messageTimestamp": timestamp,
            "pushName": "Fulano",
        },
    }


# ---------------------------------------------------------------------------
# Resposta do lead -> 'respondeu'
# ---------------------------------------------------------------------------

class TestRespostaDoLead:
    def test_mensagem_do_lead_avanca_para_respondeu(self, banco):
        criar_lead()
        webhook.processar_evento(evento_upsert("5511999990001@s.whatsapp.net", "Quanto custa o site?"))
        lead = obter_lead("place-1")
        assert lead["status"] == "respondeu"

    def test_mensagem_grava_no_cockpit_de_conversa(self, banco):
        criar_lead()
        webhook.processar_evento(evento_upsert("5511999990001@s.whatsapp.net", "Quanto custa o site?"))
        mensagens = mensagens_do_lead("place-1")
        assert len(mensagens) == 1
        assert mensagens[0]["autor"] == "lead"
        assert mensagens[0]["texto"] == "Quanto custa o site?"
        assert mensagens[0]["origem"] == "whatsapp"

    def test_numero_sem_lead_correspondente_e_ignorado(self, banco):
        criar_lead(telefone="11999990001")
        webhook.processar_evento(evento_upsert("5511999999999@s.whatsapp.net", "oi"))
        # não lançou, e não criou nada pra ninguém
        conexao = db.conectar()
        try:
            total = conexao.execute("SELECT COUNT(*) FROM mensagens_conversa").fetchone()[0]
        finally:
            conexao.close()
        assert total == 0

    def test_reenvio_do_mesmo_evento_nao_duplica(self, banco):
        criar_lead()
        evento = evento_upsert("5511999990001@s.whatsapp.net", "oi", id_externo="dup-1")
        webhook.processar_evento(evento)
        webhook.processar_evento(evento)
        assert len(mensagens_do_lead("place-1")) == 1

    def test_ja_respondeu_nao_repete_a_transicao(self, banco):
        criar_lead(status="respondeu")
        webhook.processar_evento(evento_upsert("5511999990001@s.whatsapp.net", "outra pergunta"))
        assert obter_lead("place-1")["status"] == "respondeu"

    def test_nunca_rebaixa_status_ja_fechado(self, banco):
        criar_lead(status="fechou")
        webhook.processar_evento(evento_upsert("5511999990001@s.whatsapp.net", "oi de novo"))
        assert obter_lead("place-1")["status"] == "fechou"

    def test_nunca_rebaixa_status_ignorado(self, banco):
        criar_lead(status="ignorado")
        webhook.processar_evento(evento_upsert("5511999990001@s.whatsapp.net", "oi"))
        assert obter_lead("place-1")["status"] == "ignorado"

    def test_grava_historico_status(self, banco):
        criar_lead()
        webhook.processar_evento(evento_upsert("5511999990001@s.whatsapp.net", "oi"))
        conexao = db.conectar()
        try:
            linha = conexao.execute(
                "SELECT status_anterior, status_novo FROM historico_status WHERE place_id = ?", ("place-1",)
            ).fetchone()
        finally:
            conexao.close()
        assert linha["status_anterior"] == "novo"
        assert linha["status_novo"] == "respondeu"


# ---------------------------------------------------------------------------
# Opt-out
# ---------------------------------------------------------------------------

class TestOptOut:
    @pytest.mark.parametrize("frase", [
        "Não tenho interesse, obrigada",
        "pode sair da lista",
        "PARE de mandar mensagem",
        "por favor, remover meu contato",
    ])
    def test_frases_de_optout_marcam_recusou_e_bloqueiam(self, banco, frase):
        criar_lead()
        webhook.processar_evento(evento_upsert("5511999990001@s.whatsapp.net", frase))
        lead = obter_lead("place-1")
        assert lead["status"] == "recusou"
        assert lead["wa_optout"] == 1

    def test_optout_de_lead_ja_fechado_so_liga_o_bloqueio(self, banco):
        criar_lead(status="fechou")
        webhook.processar_evento(evento_upsert("5511999990001@s.whatsapp.net", "na verdade, pare de mandar"))
        lead = obter_lead("place-1")
        assert lead["status"] == "fechou"  # não rebaixa um status terminal
        assert lead["wa_optout"] == 1  # mas o bloqueio liga de qualquer forma

    def test_palavra_pare_dentro_de_outra_palavra_nao_e_falso_positivo(self, banco):
        criar_lead()
        webhook.processar_evento(evento_upsert("5511999990001@s.whatsapp.net", "vou comparecer amanhã de manhã"))
        lead = obter_lead("place-1")
        assert lead["status"] == "respondeu"  # não confundiu "comparecer" com "pare"
        assert lead["wa_optout"] == 0

    @pytest.mark.parametrize("frase", [
        "Tenho interesse sim, te chamo depois de sair da clínica",
        "Pode mandar, mas pare um pouco pra eu ver com meu sócio primeiro",
    ])
    def test_palavra_solta_em_mensagem_longa_nao_e_optout(self, banco, frase):
        criar_lead()
        webhook.processar_evento(evento_upsert("5511999990001@s.whatsapp.net", frase))
        lead = obter_lead("place-1")
        assert lead["status"] == "respondeu"  # lead interessado não pode sumir da lista
        assert lead["wa_optout"] == 0


# ---------------------------------------------------------------------------
# fromMe (mensagem enviada fora do app)
# ---------------------------------------------------------------------------

class TestFromMe:
    def test_mensagem_fromme_fora_do_app_vira_vendedor(self, banco):
        criar_lead()
        webhook.processar_evento(
            evento_upsert("5511999990001@s.whatsapp.net", "Oi, já te retorno", from_me=True, id_externo="manual-1")
        )
        mensagens = mensagens_do_lead("place-1")
        assert len(mensagens) == 1
        assert mensagens[0]["autor"] == "vendedor"
        assert mensagens[0]["origem"] == "whatsapp"

    def test_fromme_fora_do_app_pausa_a_resposta_automatica(self, banco):
        criar_lead()
        webhook.processar_evento(
            evento_upsert("5511999990001@s.whatsapp.net", "Oi, já te retorno", from_me=True, id_externo="manual-3")
        )
        assert obter_lead("place-1")["wa_ia_pausada"] == 1

    def test_fromme_com_id_ja_registrado_nao_pausa_de_novo(self, banco):
        """O eco do próprio envio do app (mesmo id_externo) não deve contar
        como intervenção manual - só o que 'gravou' de fato."""
        criar_lead()
        agora = "2026-09-21T10:00:00"
        chave = rotas_conversa._chave_dedup("vendedor", "Oi, tudo bem?", agora, "evo-999")
        conexao = db.conectar()
        try:
            rotas_conversa._inserir_mensagem(conexao, "maps", "place-1", "vendedor", "Oi, tudo bem?", agora, "app", chave)
            conexao.commit()
        finally:
            conexao.close()

        webhook.processar_evento(
            evento_upsert("5511999990001@s.whatsapp.net", "Oi, tudo bem?", from_me=True, id_externo="evo-999")
        )
        assert obter_lead("place-1")["wa_ia_pausada"] == 0

    def test_fromme_nao_avanca_o_funil(self, banco):
        criar_lead()
        webhook.processar_evento(
            evento_upsert("5511999990001@s.whatsapp.net", "Oi!", from_me=True, id_externo="manual-2")
        )
        assert obter_lead("place-1")["status"] == "novo"  # só resposta do LEAD avança

    def test_fromme_com_id_ja_registrado_pelo_app_nao_duplica(self, banco):
        """Quando o app manda uma mensagem, a Evolution normalmente ecoa esse
        mesmo envio de volta como fromMe=true no webhook. Como a chave de dedup
        usa o mesmo id_externo, não deve duplicar no cockpit."""
        criar_lead()
        agora = "2026-09-21T10:00:00"
        chave = rotas_conversa._chave_dedup("vendedor", "Oi, tudo bem?", agora, "evo-123")
        conexao = db.conectar()
        try:
            rotas_conversa._inserir_mensagem(conexao, "maps", "place-1", "vendedor", "Oi, tudo bem?", agora, "app", chave)
            conexao.commit()
        finally:
            conexao.close()

        webhook.processar_evento(
            evento_upsert("5511999990001@s.whatsapp.net", "Oi, tudo bem?", from_me=True, id_externo="evo-123",
                           timestamp=1758445200)
        )
        # o timestamp do evento pode não bater 1:1 com `agora`, mas a chave usa
        # id_externo, então dedup funciona mesmo assim
        mensagens = mensagens_do_lead("place-1")
        assert len(mensagens) == 1
        assert mensagens[0]["origem"] == "app"  # a linha original venceu, não foi sobrescrita


# ---------------------------------------------------------------------------
# Robustez: nunca lança, sempre digestível
# ---------------------------------------------------------------------------

class TestRobustez:
    def test_payload_vazio_nao_lanca(self, banco):
        webhook.processar_evento({})

    def test_payload_nao_dict_nao_lanca(self, banco):
        webhook.processar_evento("isso nem é um objeto")

    def test_evento_desconhecido_e_ignorado(self, banco):
        webhook.processar_evento({"event": "algo.novo", "data": {}})

    def test_mensagem_sem_texto_e_ignorada(self, banco):
        criar_lead()
        webhook.processar_evento({
            "event": "messages.upsert",
            "data": {"key": {"remoteJid": "5511999990001@s.whatsapp.net", "fromMe": False, "id": "x"},
                      "message": {}, "messageTimestamp": 1758445200},
        })
        assert mensagens_do_lead("place-1") == []

    def test_connection_update_nao_lanca(self, banco):
        webhook.processar_evento({"event": "connection.update", "data": {"state": "open"}})

    def test_lista_de_mensagens_no_data_e_processada(self, banco):
        criar_lead()
        payload = {
            "event": "messages.upsert",
            "data": [
                {"key": {"remoteJid": "5511999990001@s.whatsapp.net", "fromMe": False, "id": "m1"},
                  "message": {"conversation": "primeira"}, "messageTimestamp": 1758445100},
                {"key": {"remoteJid": "5511999990001@s.whatsapp.net", "fromMe": False, "id": "m2"},
                  "message": {"conversation": "segunda"}, "messageTimestamp": 1758445200},
            ],
        }
        webhook.processar_evento(payload)
        assert len(mensagens_do_lead("place-1")) == 2


# ---------------------------------------------------------------------------
# Resposta automática (aciona o autoresponder, sem testar o autoresponder em si)
# ---------------------------------------------------------------------------

class TestAcionaAutoresponder:
    def test_mensagem_do_lead_aciona_o_autoresponder(self, banco, monkeypatch):
        chamadas = []
        monkeypatch.setattr(
            autoresponder_modulo, "processar_mensagem_recebida",
            lambda place_id, telefone: chamadas.append((place_id, telefone)),
        )
        criar_lead()
        webhook.processar_evento(evento_upsert("5511999990001@s.whatsapp.net", "Quanto custa o site?"))
        # telefone repassado é o extraído direto do JID (com o DDI 55, sem normalizar)
        assert chamadas == [("place-1", "5511999990001")]

    def test_mensagem_fromme_nao_aciona_o_autoresponder(self, banco, monkeypatch):
        chamadas = []
        monkeypatch.setattr(
            autoresponder_modulo, "processar_mensagem_recebida",
            lambda place_id, telefone: chamadas.append((place_id, telefone)),
        )
        criar_lead()
        webhook.processar_evento(
            evento_upsert("5511999990001@s.whatsapp.net", "Oi!", from_me=True, id_externo="manual-9")
        )
        assert chamadas == []
