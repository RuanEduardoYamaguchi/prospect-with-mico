"""Testes da análise de oportunidade (microdemo/analise.py, rotas_microdemo.py e
extrair_sinais_conversao). IA e rede sempre mockadas."""

import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import app as app_module
import db
import ia
import processar
import rotas_microdemo
from microdemo import analise, schema

# Mesmo motivo do test_whatsapp_rotas.py: registrar na coleta, antes de qualquer
# requisição atender o `app` compartilhado.
if "microdemo" not in app_module.app.blueprints:
    app_module.app.register_blueprint(rotas_microdemo.bp)


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


def criar_lead(place_id="place-1", nota=4.8, avaliacoes=90, site_status="sem_site", site_url=None):
    conexao = db.conectar()
    try:
        conexao.execute(
            "INSERT INTO leads (place_id, nome, categoria, endereco, nota, num_avaliacoes, "
            "site_status, site_url, nicho, cidade, status, visto_em, atualizado_em) "
            "VALUES (?, 'Clínica Sorriso', 'Dentista', 'Rua X', ?, ?, ?, ?, 'clínica odontológica', "
            "'Londrina', 'novo', '2026-09-01', '2026-09-01')",
            (place_id, nota, avaliacoes, site_status, site_url),
        )
        conexao.commit()
    finally:
        conexao.close()
    return place_id


RESPOSTA_VALIDA = {
    "recomendacao": "abordar_com_demo",
    "oportunidade": "Quem acha a clínica no Google não encontra onde marcar.",
    "evidencias": ["site: sem link de agendamento", "Google: nota 4.8 com 90 avaliações"],
    "impacto": "Perde pacientes que desistem de ligar.",
    "solucao": "Agenda no WhatsApp.",
    "micro_demo": "agendamento",
    "confianca": "alta",
    "motivo_nao_abordar": "",
    "desconhecido": ["conteúdo do Instagram"],
    "angulo": "duas pontas que não se falam",
}


class TestParser:
    def test_json_valido(self):
        assert analise._parsear(json.dumps(RESPOSTA_VALIDA)) == RESPOSTA_VALIDA

    def test_json_cercado_por_crases(self):
        bruto = "```json\n" + json.dumps(RESPOSTA_VALIDA) + "\n```"
        assert analise._parsear(bruto)["micro_demo"] == "agendamento"

    def test_enums_invalidos_viram_valores_seguros(self):
        dados = {**RESPOSTA_VALIDA, "recomendacao": "talvez", "micro_demo": "robo",
                 "confianca": "altíssima"}
        resultado = analise._parsear(json.dumps(dados))
        assert resultado["recomendacao"] == "nao_abordar"
        assert resultado["micro_demo"] == "nenhuma"
        assert resultado["confianca"] == "baixa"

    def test_string_onde_se_espera_lista(self):
        dados = {**RESPOSTA_VALIDA, "evidencias": "só uma evidência", "desconhecido": ""}
        resultado = analise._parsear(json.dumps(dados))
        assert resultado["evidencias"] == ["só uma evidência"]
        assert resultado["desconhecido"] == []

    def test_campos_ausentes_ficam_vazios(self):
        resultado = analise._parsear("{}")
        assert resultado["recomendacao"] == "nao_abordar"
        assert resultado["oportunidade"] == ""
        assert resultado["evidencias"] == []

    def test_trunca_textos_e_listas(self):
        dados = {**RESPOSTA_VALIDA, "oportunidade": "a" * 2000, "evidencias": ["b" * 1000] * 10}
        resultado = analise._parsear(json.dumps(dados))
        assert len(resultado["oportunidade"]) == analise.MAX_CHARS_CAMPO
        assert len(resultado["evidencias"]) == analise.MAX_ITENS_LISTA
        assert len(resultado["evidencias"][0]) == analise.MAX_CHARS_ITEM

    def test_json_invalido_levanta(self):
        with pytest.raises(ValueError):
            analise._parsear("isso não é json")


class TestSinaisDeConversao:
    def test_doctoralia_vira_agendamento(self):
        html = '<a href="https://www.doctoralia.com.br/clinica">Marcar</a>'
        sinais = processar.extrair_sinais_conversao(html)
        assert "agendamento online (www.doctoralia.com.br)" in sinais["encontrados"]
        assert "pedido ou cardápio online" in sinais["nao_encontrados"]

    def test_ifood_vira_pedido(self):
        sinais = processar.extrair_sinais_conversao('<a href="https://ifood.com.br/loja">Peça</a>')
        assert any(s.startswith("pedido ou cardápio online (") for s in sinais["encontrados"])

    def test_link_com_texto_agendar(self):
        sinais = processar.extrair_sinais_conversao('<a href="/x">Agende sua consulta</a>')
        assert any(s.startswith("agendamento online") for s in sinais["encontrados"])

    def test_formulario(self):
        sinais = processar.extrair_sinais_conversao("<form action='/x'></form>")
        assert "formulário de contato" in sinais["encontrados"]

    def test_pagina_vazia_nao_encontra_nada(self):
        sinais = processar.extrair_sinais_conversao("<html><body>oi</body></html>")
        assert sinais["encontrados"] == []
        assert sinais["nao_encontrados"] == [
            "agendamento online", "pedido ou cardápio online", "formulário de contato"]


class TestPrompt:
    def test_system_tem_catalogo_e_contrato(self):
        system = analise.montar_system()
        assert "negócio" in system
        for chave in ("agendamento", "pedido", "nenhuma"):
            assert f'"{chave}"' in system
        for campo in ("recomendacao", "evidencias", "motivo_nao_abordar", "desconhecido", "angulo"):
            assert f'"{campo}"' in system
        assert "—" not in system

    def test_user_lista_o_que_nao_e_verificavel(self):
        lead = {"nome": "Clínica Sorriso", "nota": 4.8, "num_avaliacoes": 90,
                "site_status": "sem_site", "instagram_url": None}
        sinais = {"encontrados": [], "nao_encontrados": ["agendamento online"]}
        user = analise.montar_user(lead, None, sinais, 85)
        assert "NÃO consegue verificar" in user
        assert "Instagram" in user
        assert "Clínica Sorriso" in user


class TestRotas:
    def test_lead_inexistente_404(self, cliente):
        assert cliente.get("/api/leads/nao-existe/oportunidade").status_code == 404
        assert cliente.post("/api/leads/nao-existe/oportunidade/analisar").status_code == 404

    def test_get_sem_analise(self, cliente):
        criar_lead()
        corpo = cliente.get("/api/leads/place-1/oportunidade").get_json()
        assert corpo["analise"] is None
        assert corpo["score_min"] == 70
        assert isinstance(corpo["score"], int)

    def test_score_abaixo_do_minimo_devolve_400(self, cliente, monkeypatch):
        criar_lead(nota=4.0, avaliacoes=5, site_status="site_ok")
        monkeypatch.setattr(ia, "executar_com_fallback",
                            lambda *a, **k: pytest.fail("não deveria chamar a IA"))
        resposta = cliente.post("/api/leads/place-1/oportunidade/analisar")
        assert resposta.status_code == 400
        assert "abaixo do mínimo para análise (70)" in resposta.get_json()["erro"]

    def test_analise_persistida_e_devolvida_no_get(self, cliente, monkeypatch):
        criar_lead(site_url="https://clinica.example")
        html = '<html><title>Clínica</title><a href="https://calendly.com/x">oi</a></html>'
        monkeypatch.setattr(processar, "_baixar_html", lambda url: html)
        capturado = {}

        def ia_falsa(system, user, **kwargs):
            capturado.update(user=user, **kwargs)
            return analise._parsear(json.dumps(RESPOSTA_VALIDA)), "gemini", ["aviso"]

        monkeypatch.setattr(ia, "executar_com_fallback", ia_falsa)

        resposta = cliente.post("/api/leads/place-1/oportunidade/analisar")
        assert resposta.status_code == 200
        feita = resposta.get_json()["analise"]
        assert feita["provedor"] == "gemini"
        assert feita["avisos"] == ["aviso"]
        assert feita["micro_demo"] == "agendamento"
        assert feita["score_no_momento"] >= 70
        assert "criada_em" in feita
        assert "calendly" in capturado["user"]
        assert capturado["max_tokens"] == 1400

        lida = cliente.get("/api/leads/place-1/oportunidade").get_json()["analise"]
        assert lida["evidencias"] == RESPOSTA_VALIDA["evidencias"]
        assert lida["recomendacao"] == "abordar_com_demo"
        assert lida["provedor"] == "gemini"

    def test_sem_provedor_devolve_500_amigavel(self, cliente, monkeypatch):
        criar_lead()

        def sem_ia(*a, **k):
            raise ia.NenhumProvedorDisponivel(None)

        monkeypatch.setattr(ia, "executar_com_fallback", sem_ia)
        resposta = cliente.post("/api/leads/place-1/oportunidade/analisar")
        assert resposta.status_code == 500
        assert "erro" in resposta.get_json()


class TestConfiguracaoScoreMinimo:
    def test_padrao_70(self, cliente):
        assert cliente.get("/api/configuracoes/analise-oportunidade").get_json() == {"score_min": 70}

    def test_salva_e_le(self, cliente):
        resposta = cliente.post("/api/configuracoes/analise-oportunidade", json={"score_min": 55})
        assert resposta.get_json() == {"score_min": 55}
        assert cliente.get("/api/configuracoes/analise-oportunidade").get_json() == {"score_min": 55}

    @pytest.mark.parametrize("valor", [-1, 101, "70", 70.5, None, True])
    def test_valor_invalido_400(self, cliente, valor):
        resposta = cliente.post("/api/configuracoes/analise-oportunidade", json={"score_min": valor})
        assert resposta.status_code == 400
        assert "erro" in resposta.get_json()
