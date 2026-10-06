"""Testes do diagnóstico em PDF - PageSpeed e configs mockados, sem rede real."""

import sqlite3

import pytest

import app as app_module
import db
import diagnostico
import processar


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    caminho_banco_teste = tmp_path / "leads_teste.db"
    monkeypatch.setattr(db, "CAMINHO_BANCO", caminho_banco_teste)
    # PageSpeed nunca é consultado de verdade nos testes
    monkeypatch.setattr(diagnostico, "consultar_pagespeed", lambda url: None)

    conexao = sqlite3.connect(caminho_banco_teste)
    processar.preparar_banco(conexao)
    conexao.close()

    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as cliente_teste:
        yield cliente_teste


def inserir_lead(place_id="lead-1", **overrides):
    campos = {
        "place_id": place_id,
        "nome": "Clínica Estética Vitória",
        "categoria": "Clínica de estética",
        "cidade": "Vitória - ES",
        "nota": 4.9,
        "num_avaliacoes": 87,
        "status": "novo",
        "site_status": "sem_site",
        "site_url": None,
        "site_problemas": None,
        "visto_em": "2026-01-01",
        "atualizado_em": "2026-01-01T00:00:00",
    }
    campos.update(overrides)
    conexao = sqlite3.connect(db.CAMINHO_BANCO)
    conexao.execute(
        """
        INSERT INTO leads (place_id, nome, categoria, cidade, nota, num_avaliacoes, status,
                           site_status, site_url, site_problemas, visto_em, atualizado_em)
        VALUES (:place_id, :nome, :categoria, :cidade, :nota, :num_avaliacoes, :status,
                :site_status, :site_url, :site_problemas, :visto_em, :atualizado_em)
        """,
        campos,
    )
    conexao.commit()
    conexao.close()


def buscar_lead(place_id="lead-1"):
    conexao = sqlite3.connect(db.CAMINHO_BANCO)
    conexao.row_factory = sqlite3.Row
    lead = conexao.execute("SELECT * FROM leads WHERE place_id = ?", (place_id,)).fetchone()
    conexao.close()
    return lead


class TestGeracaoDoPdf:
    def test_pdf_valido_para_lead_sem_site(self, cliente):
        inserir_lead()
        pdf = diagnostico.gerar_diagnostico_pdf(buscar_lead())
        assert pdf.startswith(b"%PDF")
        assert len(pdf) > 1000

    def test_pdf_valido_para_lead_com_site_ruim(self, cliente):
        inserir_lead(
            site_status="site_ruim",
            site_url="https://clinica.com.br",
            site_problemas="não adaptado para celular; sem HTTPS (aparece como 'não seguro' no navegador)",
        )
        pdf = diagnostico.gerar_diagnostico_pdf(buscar_lead())
        assert pdf.startswith(b"%PDF")

    def test_pdf_inclui_secao_pagespeed_quando_disponivel(self, cliente, monkeypatch):
        monkeypatch.setattr(
            diagnostico, "consultar_pagespeed",
            lambda url: {"nota": 34, "tempo_carregamento": "6,2 s"},
        )
        inserir_lead(
            site_status="site_ruim",
            site_url="https://clinica.com.br",
            site_problemas="página quase vazia",
        )
        pdf = diagnostico.gerar_diagnostico_pdf(buscar_lead())
        assert pdf.startswith(b"%PDF")

    def test_construtor_pronto_tem_explicacao(self, cliente):
        inserir_lead(
            site_status="site_ruim",
            site_url="https://x.wixsite.com/clinica",
            site_problemas="feito em construtor pronto (Wix)",
        )
        pdf = diagnostico.gerar_diagnostico_pdf(buscar_lead())
        assert pdf.startswith(b"%PDF")

    def test_nome_do_arquivo_e_slugificado(self):
        assert diagnostico.nome_arquivo_diagnostico("Clínica São João!") == "diagnostico-cl-nica-s-o-jo-o.pdf"
        assert diagnostico.nome_arquivo_diagnostico(None) == "diagnostico-lead.pdf"


class TestRotaDoDiagnostico:
    def test_rota_retorna_pdf(self, cliente):
        inserir_lead()
        resposta = cliente.get("/api/leads/lead-1/diagnostico.pdf")
        assert resposta.status_code == 200
        assert resposta.mimetype == "application/pdf"
        assert resposta.data.startswith(b"%PDF")
        assert "attachment" in resposta.headers["Content-Disposition"]

    def test_lead_inexistente_retorna_404(self, cliente):
        assert cliente.get("/api/leads/nao-existe/diagnostico.pdf").status_code == 404


class TestConsultarPagespeed:
    def test_resposta_valida(self, monkeypatch):
        import requests

        class RespostaPsi:
            status_code = 200

            def json(self):
                return {"lighthouseResult": {
                    "categories": {"performance": {"score": 0.34}},
                    "audits": {"largest-contentful-paint": {"displayValue": "6,2 s"}},
                }}

        monkeypatch.setattr(requests, "get", lambda *a, **kw: RespostaPsi())
        resultado = diagnostico.consultar_pagespeed("https://x.com.br")
        assert resultado == {"nota": 34, "tempo_carregamento": "6,2 s"}

    def test_falha_retorna_none(self, monkeypatch):
        import requests

        def explode(*a, **kw):
            raise requests.exceptions.Timeout("psi demorou")

        monkeypatch.setattr(requests, "get", explode)
        assert diagnostico.consultar_pagespeed("https://x.com.br") is None
