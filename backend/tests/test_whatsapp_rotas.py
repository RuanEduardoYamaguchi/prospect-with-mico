"""Testes das rotas de whatsapp/campanhas (rotas_whatsapp.py): validação,
status HTTP e a "cola" entre a rota e whatsapp/*.py. A lógica de filtro e do
motor de campanha já é coberta por test_whatsapp_campanha.py - aqui o que
importa é o contrato HTTP (INTEGRACAO.md): formato do JSON e quando cada rota
devolve 400/404/200.

Evolution é sempre mockada (monkeypatch direto nas funções de whatsapp/evolution.py) -
nenhum teste aqui toca rede.
"""

import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import app as app_module
import db
import processar
import rotas_whatsapp
from whatsapp import aquecimento, campanha, evolution, schema

# Registrado na COLETA (import do módulo de teste), não dentro de uma fixture:
# o Flask trava novo register_blueprint depois da primeira requisição atendida,
# e outros arquivos de teste (test_app.py etc.) já batem requisição real no
# mesmo `app_module.app` compartilhado antes deste arquivo rodar. Import
# acontece antes de qualquer teste EXECUTAR (fase de coleta do pytest), então
# isso sempre corre a tempo.
if "whatsapp" not in app_module.app.blueprints:
    app_module.app.register_blueprint(rotas_whatsapp.bp)


@pytest.fixture
def banco(tmp_path, monkeypatch):
    caminho = tmp_path / "leads_teste.db"
    monkeypatch.setattr(db, "CAMINHO_BANCO", caminho)
    cofre = {}
    monkeypatch.setattr(db, "_keyring_obter", cofre.get)
    monkeypatch.setattr(db, "_keyring_salvar", lambda c, v: cofre.update({c: v}) or True)
    monkeypatch.setattr(db, "_keyring_apagar", lambda c: cofre.pop(c, None))
    conexao = sqlite3.connect(caminho)
    try:
        processar.preparar_banco(conexao)
        schema.preparar(conexao)
    finally:
        conexao.close()
    return caminho


@pytest.fixture
def cliente(banco):
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c


def criar_lead(place_id="place-1", nome="Clínica Sorriso", telefone="11999990001",
                 status="novo", wa_optout=0):
    conexao = db.conectar()
    try:
        conexao.execute(
            "INSERT INTO leads (place_id, nome, categoria, endereco, nota, num_avaliacoes, "
            "telefone, whatsapp_link, site_status, status, wa_optout, visto_em, atualizado_em) "
            "VALUES (?, ?, 'Clínica', 'Rua X', 4.8, 90, ?, ?, 'sem_site', ?, ?, '2026-09-01', '2026-09-01')",
            (place_id, nome, telefone, f"https://wa.me/55{telefone}", status, wa_optout),
        )
        conexao.commit()
    finally:
        conexao.close()
    return place_id


# ---------------------------------------------------------------------------
# Conexão
# ---------------------------------------------------------------------------

class TestEstadoEConexao:
    def test_estado_repassa_o_que_a_evolution_diz(self, cliente, monkeypatch):
        monkeypatch.setattr(evolution, "estado", lambda: {
            "evolution_ok": True, "conectado": True, "estado": "open",
            "numero": "5541999990000", "instancia": "prospector",
        })
        dados = cliente.get("/api/whatsapp/estado").get_json()
        assert dados["conectado"] is True
        assert dados["instancia"] == "prospector"

    def test_conectar_devolve_qr(self, cliente, monkeypatch):
        monkeypatch.setattr(evolution, "conectar", lambda: {"estado": "connecting", "qr_base64": "data:image/png;base64,ABC"})
        dados = cliente.post("/api/whatsapp/conectar").get_json()
        assert dados["qr_base64"].startswith("data:image/png;base64,")

    def test_conectar_evolution_fora_do_ar_vira_erro_amigavel(self, cliente, monkeypatch):
        def falhar():
            raise evolution.ErroEvolution("Não foi possível falar com a Evolution API.")
        monkeypatch.setattr(evolution, "conectar", falhar)
        resposta = cliente.post("/api/whatsapp/conectar")
        assert resposta.status_code in (500, 502, 503)
        assert "erro" in resposta.get_json()

    def test_desconectar_ok(self, cliente, monkeypatch):
        monkeypatch.setattr(evolution, "desconectar", lambda: None)
        assert cliente.post("/api/whatsapp/desconectar").get_json() == {"ok": True}


class TestAquecimento:
    def test_aquecimento_repassa_o_resumo(self, cliente, monkeypatch):
        monkeypatch.setattr(aquecimento, "resumo", lambda: {
            "dia_do_chip": 3, "teto_hoje": 25, "enviados_hoje": 5,
            "restantes_hoje": 20, "falhas_ontem": 0,
        })
        dados = cliente.get("/api/whatsapp/aquecimento").get_json()
        assert dados["teto_hoje"] == 25


# ---------------------------------------------------------------------------
# Envio manual
# ---------------------------------------------------------------------------

class TestEnviarManual:
    def _preparar_ambiente_ok(self, monkeypatch):
        monkeypatch.setattr(campanha, "telefone_ja_recebeu", lambda numero: False)
        monkeypatch.setattr(aquecimento, "resumo", lambda: {
            "dia_do_chip": 1, "teto_hoje": 15, "enviados_hoje": 0, "restantes_hoje": 15, "falhas_ontem": 0,
        })
        monkeypatch.setattr(evolution, "estado", lambda: {
            "evolution_ok": True, "conectado": True, "estado": "open", "numero": "x", "instancia": "prospector",
        })

    def test_place_id_vazio_400(self, cliente):
        assert cliente.post("/api/whatsapp/enviar", json={"texto": "oi"}).status_code == 400

    def test_texto_vazio_400(self, cliente):
        criar_lead()
        resposta = cliente.post("/api/whatsapp/enviar", json={"place_id": "place-1", "texto": "   "})
        assert resposta.status_code == 400

    def test_lead_inexistente_404(self, cliente):
        resposta = cliente.post("/api/whatsapp/enviar", json={"place_id": "nao-existe", "texto": "oi"})
        assert resposta.status_code == 404

    def test_lead_com_optout_400(self, cliente):
        criar_lead(wa_optout=1)
        resposta = cliente.post("/api/whatsapp/enviar", json={"place_id": "place-1", "texto": "oi"})
        assert resposta.status_code == 400
        assert "não receber" in resposta.get_json()["erro"]

    def test_numero_ja_recebeu_400(self, cliente, monkeypatch):
        criar_lead()
        monkeypatch.setattr(campanha, "telefone_ja_recebeu", lambda numero: True)
        resposta = cliente.post("/api/whatsapp/enviar", json={"place_id": "place-1", "texto": "oi"})
        assert resposta.status_code == 400

    def test_followup_pode_ir_pra_quem_ja_recebeu(self, cliente, monkeypatch):
        criar_lead()
        self._preparar_ambiente_ok(monkeypatch)
        monkeypatch.setattr(campanha, "telefone_ja_recebeu", lambda numero: True)
        monkeypatch.setattr(evolution, "enviar_texto", lambda numero, texto: {"key": {"id": "abc"}})
        monkeypatch.setattr(campanha, "registrar_envio_manual", lambda *a, **k: {"status": "enviado"})
        resposta = cliente.post("/api/whatsapp/enviar",
                                json={"place_id": "place-1", "texto": "oi de novo", "followup": True})
        assert resposta.status_code == 200

    def test_resposta_a_lead_que_respondeu_ignora_o_teto(self, cliente, monkeypatch):
        criar_lead(status="respondeu")
        self._preparar_ambiente_ok(monkeypatch)
        monkeypatch.setattr(aquecimento, "resumo", lambda: {
            "dia_do_chip": 1, "teto_hoje": 15, "enviados_hoje": 15, "restantes_hoje": 0, "falhas_ontem": 0,
        })
        monkeypatch.setattr(evolution, "enviar_texto", lambda numero, texto: {"key": {"id": "abc"}})
        monkeypatch.setattr(campanha, "registrar_envio_manual", lambda *a, **k: {"status": "enviado"})
        resposta = cliente.post("/api/whatsapp/enviar",
                                json={"place_id": "place-1", "texto": "claro, te mando", "followup": True})
        assert resposta.status_code == 200

    def test_followup_respeita_optout(self, cliente):
        criar_lead(wa_optout=1)
        resposta = cliente.post("/api/whatsapp/enviar",
                                json={"place_id": "place-1", "texto": "oi", "followup": True})
        assert resposta.status_code == 400

    def test_teto_esgotado_400(self, cliente, monkeypatch):
        criar_lead()
        monkeypatch.setattr(campanha, "telefone_ja_recebeu", lambda numero: False)
        monkeypatch.setattr(aquecimento, "resumo", lambda: {
            "dia_do_chip": 1, "teto_hoje": 15, "enviados_hoje": 15, "restantes_hoje": 0, "falhas_ontem": 0,
        })
        resposta = cliente.post("/api/whatsapp/enviar", json={"place_id": "place-1", "texto": "oi"})
        assert resposta.status_code == 400
        assert "teto" in resposta.get_json()["erro"]

    def test_desconectado_400(self, cliente, monkeypatch):
        criar_lead()
        monkeypatch.setattr(campanha, "telefone_ja_recebeu", lambda numero: False)
        monkeypatch.setattr(aquecimento, "resumo", lambda: {
            "dia_do_chip": 1, "teto_hoje": 15, "enviados_hoje": 0, "restantes_hoje": 15, "falhas_ontem": 0,
        })
        monkeypatch.setattr(evolution, "estado", lambda: {
            "evolution_ok": True, "conectado": False, "estado": "close", "numero": None, "instancia": "prospector",
        })
        resposta = cliente.post("/api/whatsapp/enviar", json={"place_id": "place-1", "texto": "oi"})
        assert resposta.status_code == 400
        assert "conectado" in resposta.get_json()["erro"]

    def test_envio_com_sucesso(self, cliente, monkeypatch):
        criar_lead()
        self._preparar_ambiente_ok(monkeypatch)
        monkeypatch.setattr(evolution, "enviar_texto", lambda numero, texto: {"key": {"id": "abc123"}})
        chamadas = {}

        def registrar_fake(place_id, telefone, texto, status, erro=None, id_externo=None):
            chamadas["args"] = (place_id, telefone, texto, status, erro, id_externo)
            return {"id": 1, "place_id": place_id, "telefone": telefone, "texto": texto,
                     "status": status, "erro": erro, "id_externo": id_externo, "enviado_em": "2026-09-21T10:00:00"}

        monkeypatch.setattr(campanha, "registrar_envio_manual", registrar_fake)

        resposta = cliente.post("/api/whatsapp/enviar", json={"place_id": "place-1", "texto": "Oi {{nome}}!"})
        assert resposta.status_code == 200
        dados = resposta.get_json()
        assert dados["ok"] is True
        assert dados["envio"]["status"] == "enviado"
        assert chamadas["args"][2] == "Oi Clínica Sorriso!"  # variável já resolvida
        assert chamadas["args"][5] == "abc123"  # id_externo

    def test_falha_no_envio_e_registrada_e_devolve_erro(self, cliente, monkeypatch):
        criar_lead()
        self._preparar_ambiente_ok(monkeypatch)

        def falhar(numero, texto):
            raise evolution.ErroEvolution("número inválido", status=400)
        monkeypatch.setattr(evolution, "enviar_texto", falhar)

        chamadas = []
        monkeypatch.setattr(campanha, "registrar_envio_manual",
                              lambda *a, **k: chamadas.append((a, k)) or {})

        resposta = cliente.post("/api/whatsapp/enviar", json={"place_id": "place-1", "texto": "oi"})
        assert resposta.status_code == 400
        assert chamadas  # registrou a falha


# ---------------------------------------------------------------------------
# Envio avulso (sem lead cadastrado)
# ---------------------------------------------------------------------------

class TestEnviarNumero:
    def test_texto_vazio_400(self, cliente):
        resposta = cliente.post("/api/whatsapp/enviar-numero", json={"telefone": "65999998888", "texto": "  "})
        assert resposta.status_code == 400

    def test_telefone_invalido_400(self, cliente):
        resposta = cliente.post("/api/whatsapp/enviar-numero", json={"telefone": "123", "texto": "oi"})
        assert resposta.status_code == 400

    def test_desconectado_400(self, cliente, monkeypatch):
        monkeypatch.setattr(evolution, "estado", lambda: {
            "evolution_ok": True, "conectado": False, "estado": "close", "numero": None, "instancia": "prospector",
        })
        resposta = cliente.post("/api/whatsapp/enviar-numero", json={"telefone": "65999998888", "texto": "oi"})
        assert resposta.status_code == 400
        assert "conectado" in resposta.get_json()["erro"]

    def test_envio_sem_lead_correspondente(self, cliente, monkeypatch):
        monkeypatch.setattr(evolution, "estado", lambda: {
            "evolution_ok": True, "conectado": True, "estado": "open", "numero": "x", "instancia": "prospector",
        })
        enviados = []
        monkeypatch.setattr(evolution, "enviar_texto", lambda numero, texto: enviados.append((numero, texto)) or {"key": {"id": "abc"}})
        chamadas_registro = []
        monkeypatch.setattr(campanha, "registrar_envio_manual", lambda *a, **k: chamadas_registro.append((a, k)) or {})

        resposta = cliente.post("/api/whatsapp/enviar-numero", json={"telefone": "65999998888", "texto": "oi, tudo bem?"})
        assert resposta.status_code == 200
        dados = resposta.get_json()
        assert dados["ok"] is True
        assert dados["numero"] == "5565999998888"
        assert enviados == [("5565999998888", "oi, tudo bem?")]
        assert chamadas_registro == []  # sem lead correspondente, não grava no cockpit

    def test_envio_com_lead_correspondente_grava_no_cockpit(self, cliente, monkeypatch):
        criar_lead(telefone="65999998888")
        monkeypatch.setattr(evolution, "estado", lambda: {
            "evolution_ok": True, "conectado": True, "estado": "open", "numero": "x", "instancia": "prospector",
        })
        monkeypatch.setattr(evolution, "enviar_texto", lambda numero, texto: {"key": {"id": "abc"}})
        chamadas_registro = []
        monkeypatch.setattr(campanha, "registrar_envio_manual", lambda *a, **k: chamadas_registro.append((a, k)) or {})

        resposta = cliente.post("/api/whatsapp/enviar-numero", json={"telefone": "65999998888", "texto": "oi"})
        assert resposta.status_code == 200
        assert len(chamadas_registro) == 1
        assert chamadas_registro[0][0][0] == "place-1"  # place_id do lead resolvido

    def test_falha_no_envio_devolve_erro(self, cliente, monkeypatch):
        monkeypatch.setattr(evolution, "estado", lambda: {
            "evolution_ok": True, "conectado": True, "estado": "open", "numero": "x", "instancia": "prospector",
        })

        def falhar(numero, texto):
            raise evolution.ErroEvolution("número inválido", status=400)
        monkeypatch.setattr(evolution, "enviar_texto", falhar)

        resposta = cliente.post("/api/whatsapp/enviar-numero", json={"telefone": "65999998888", "texto": "oi"})
        assert resposta.status_code == 400


# ---------------------------------------------------------------------------
# Webhook
# ---------------------------------------------------------------------------

class TestWebhook:
    def test_sempre_200(self, cliente, monkeypatch):
        chamou = []
        monkeypatch.setattr(rotas_whatsapp.webhook, "processar_evento", lambda payload: chamou.append(payload))
        resposta = cliente.post("/api/whatsapp/webhook", json={"event": "messages.upsert", "data": {}})
        assert resposta.status_code == 200
        assert chamou == [{"event": "messages.upsert", "data": {}}]

    def test_corpo_vazio_nao_quebra(self, cliente, monkeypatch):
        monkeypatch.setattr(rotas_whatsapp.webhook, "processar_evento", lambda payload: None)
        assert cliente.post("/api/whatsapp/webhook").status_code == 200


# ---------------------------------------------------------------------------
# Campanhas
# ---------------------------------------------------------------------------

class TestPreviaCampanha:
    def test_template_vazio_400(self, cliente):
        assert cliente.post("/api/campanhas/previa", json={"filtros": {}, "template": "  "}).status_code == 400

    def test_repassa_para_campanha_previa(self, cliente, monkeypatch):
        monkeypatch.setattr(campanha, "previa", lambda filtros, template, limite: {
            "leads": [], "total": 0, "descartados": {}, "teto_restante": 15, "aviso": None,
        })
        resposta = cliente.post("/api/campanhas/previa", json={"filtros": {}, "template": "Oi"})
        assert resposta.status_code == 200
        assert resposta.get_json()["teto_restante"] == 15


class TestCriarCampanha:
    def _corpo_ok(self):
        return {"filtros": {}, "template": "Oi {{nome}}", "limite": 10}

    def _preparar_ambiente_ok(self, monkeypatch, leads=None):
        monkeypatch.setattr(campanha, "existe_campanha_ativa", lambda: None)
        monkeypatch.setattr(evolution, "estado", lambda: {
            "evolution_ok": True, "conectado": True, "estado": "open", "numero": "x", "instancia": "prospector",
        })
        monkeypatch.setattr(campanha, "previa", lambda filtros, template, limite: {
            "leads": leads if leads is not None else [{"place_id": "p1"}],
            "total": 1, "descartados": {}, "teto_restante": 15, "aviso": None,
        })

    def test_template_vazio_400(self, cliente):
        assert cliente.post("/api/campanhas", json={"filtros": {}, "template": ""}).status_code == 400

    def test_template_com_link_400(self, cliente):
        resposta = cliente.post("/api/campanhas", json={"filtros": {}, "template": "Olha www.exemplo.com"})
        assert resposta.status_code == 400
        assert "link" in resposta.get_json()["erro"]

    def test_template_com_marcador_preencher_400(self, cliente):
        resposta = cliente.post(
            "/api/campanhas",
            json={"filtros": {}, "template": "Oi! Aqui é o [PREENCHER: seu nome], da [PREENCHER: sua empresa]."},
        )
        assert resposta.status_code == 400
        assert "PREENCHER" in resposta.get_json()["erro"]

    def test_campanha_ja_ativa_400(self, cliente, monkeypatch):
        monkeypatch.setattr(campanha, "existe_campanha_ativa", lambda: {"id": 1, "status": "rodando"})
        resposta = cliente.post("/api/campanhas", json=self._corpo_ok())
        assert resposta.status_code == 400

    def test_desconectado_400(self, cliente, monkeypatch):
        monkeypatch.setattr(campanha, "existe_campanha_ativa", lambda: None)
        monkeypatch.setattr(evolution, "estado", lambda: {
            "evolution_ok": True, "conectado": False, "estado": "close", "numero": None, "instancia": "prospector",
        })
        resposta = cliente.post("/api/campanhas", json=self._corpo_ok())
        assert resposta.status_code == 400

    def test_lista_vazia_400(self, cliente, monkeypatch):
        self._preparar_ambiente_ok(monkeypatch, leads=[])
        resposta = cliente.post("/api/campanhas", json=self._corpo_ok())
        assert resposta.status_code == 400

    def test_criacao_com_sucesso(self, cliente, monkeypatch):
        self._preparar_ambiente_ok(monkeypatch)
        chamadas = {}

        def criar_fake(nome, filtros, template, limite, ritmo, checar_whatsapp):
            chamadas["args"] = (nome, filtros, template, limite, ritmo, checar_whatsapp)
            return {"id": 1, "status": "rodando"}

        monkeypatch.setattr(campanha, "criar_campanha", criar_fake)
        resposta = cliente.post("/api/campanhas", json=self._corpo_ok())
        assert resposta.status_code == 200
        assert resposta.get_json()["campanha"]["id"] == 1
        assert chamadas["args"][5] is True  # checar_whatsapp default


class TestListarPararRetomarDescartar:
    def test_listar_repassa(self, cliente, monkeypatch):
        monkeypatch.setattr(campanha, "listar", lambda: {"ativa": None, "historico": []})
        assert cliente.get("/api/campanhas").get_json() == {"ativa": None, "historico": []}

    def test_parar_sucesso(self, cliente, monkeypatch):
        monkeypatch.setattr(campanha, "parar", lambda campanha_id: ({"id": campanha_id, "status": "pausada"}, None))
        resposta = cliente.post("/api/campanhas/1/parar")
        assert resposta.get_json()["campanha"]["status"] == "pausada"

    def test_parar_nao_encontrada_404(self, cliente, monkeypatch):
        monkeypatch.setattr(campanha, "parar", lambda campanha_id: (None, "campanha não encontrada"))
        assert cliente.post("/api/campanhas/999/parar").status_code == 404

    def test_retomar_exige_conexao(self, cliente, monkeypatch):
        monkeypatch.setattr(evolution, "estado", lambda: {
            "evolution_ok": True, "conectado": False, "estado": "close", "numero": None, "instancia": "prospector",
        })
        resposta = cliente.post("/api/campanhas/1/retomar")
        assert resposta.status_code == 400

    def test_retomar_sucesso(self, cliente, monkeypatch):
        monkeypatch.setattr(evolution, "estado", lambda: {
            "evolution_ok": True, "conectado": True, "estado": "open", "numero": "x", "instancia": "prospector",
        })
        monkeypatch.setattr(campanha, "retomar", lambda campanha_id: ({"id": campanha_id, "status": "rodando"}, None))
        resposta = cliente.post("/api/campanhas/1/retomar")
        assert resposta.get_json()["campanha"]["status"] == "rodando"

    def test_descartar_sucesso(self, cliente, monkeypatch):
        monkeypatch.setattr(campanha, "descartar", lambda campanha_id: ({"id": campanha_id, "status": "parada"}, None))
        resposta = cliente.post("/api/campanhas/1/descartar")
        assert resposta.get_json()["campanha"]["status"] == "parada"


class TestAutoresposta:
    def test_padrao_desligada(self, cliente):
        assert cliente.get("/api/whatsapp/autoresposta").get_json() == {"ativa": False}

    def test_desliga_e_religa_persistindo(self, cliente):
        resposta = cliente.post("/api/whatsapp/autoresposta", json={"ativa": False})
        assert resposta.get_json() == {"ativa": False}
        assert cliente.get("/api/whatsapp/autoresposta").get_json() == {"ativa": False}
        cliente.post("/api/whatsapp/autoresposta", json={"ativa": True})
        assert cliente.get("/api/whatsapp/autoresposta").get_json() == {"ativa": True}

    @pytest.mark.parametrize("corpo", [{}, {"ativa": "sim"}, {"ativa": 1}, {"ativa": None}])
    def test_valor_invalido_400(self, cliente, corpo):
        assert cliente.post("/api/whatsapp/autoresposta", json=corpo).status_code == 400


class TestIaPausada:
    def test_pausa_e_despausa(self, cliente):
        criar_lead()
        resposta = cliente.post("/api/leads/place-1/ia-pausada", json={"pausada": True})
        assert resposta.get_json() == {"ok": True, "pausada": True}
        conexao = db.conectar()
        try:
            assert conexao.execute("SELECT wa_ia_pausada FROM leads WHERE place_id='place-1'").fetchone()[0] == 1
        finally:
            conexao.close()
        cliente.post("/api/leads/place-1/ia-pausada", json={"pausada": False})
        conexao = db.conectar()
        try:
            assert conexao.execute("SELECT wa_ia_pausada FROM leads WHERE place_id='place-1'").fetchone()[0] == 0
        finally:
            conexao.close()

    def test_lead_inexistente_404(self, cliente):
        assert cliente.post("/api/leads/nao-existe/ia-pausada", json={"pausada": True}).status_code == 404

    def test_valor_invalido_400(self, cliente):
        criar_lead()
        assert cliente.post("/api/leads/place-1/ia-pausada", json={"pausada": "sim"}).status_code == 400
