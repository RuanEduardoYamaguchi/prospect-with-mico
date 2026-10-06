"""Testes do funil transparente da busca (bugs relatados por usuários:
"no Google tem 20 leads e o app puxou só 2" - os descartes eram silenciosos).

Cobre os contadores novos de processar.processar e a mensagem final montada
por jobs.montar_mensagem_conclusao.
"""

import csv
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import db
import jobs
import processar


# ---------------------------------------------------------------------------
# montar_mensagem_conclusao - a mensagem que explica o funil
# ---------------------------------------------------------------------------

class TestMontarMensagemConclusao:
    def test_funil_completo_explicado(self):
        # o cenário da reclamação: 20 capturadas, só 2 viraram leads
        mensagem = jobs.montar_mensagem_conclusao({
            "total_no_csv": 20,
            "novos": 2,
            "novos_sem_site": 1,
            "novos_site_ruim": 1,
            "descartados_por_site_ok": 15,
            "descartados_nota_baixa": 2,
            "descartados_sem_telefone": 1,
            "erros_de_linha": 0,
        })
        assert "2 lead(s) novo(s)" in mensagem
        assert "Das 20 empresas capturadas" in mensagem
        assert "15 já têm site bom" in mensagem
        assert "2 com nota baixa" in mensagem
        assert "1 sem telefone" in mensagem

    def test_ja_conhecidos_aparecem(self):
        # 10 capturadas, 3 novas, 7 já estavam na base (dedup silencioso)
        mensagem = jobs.montar_mensagem_conclusao({
            "total_no_csv": 10,
            "novos": 3,
            "novos_sem_site": 3,
            "novos_site_ruim": 0,
            "descartados_por_site_ok": 0,
            "descartados_nota_baixa": 0,
            "descartados_sem_telefone": 0,
            "erros_de_linha": 0,
        })
        assert "7 já estavam na sua base" in mensagem

    def test_nenhum_lead_novo_ainda_explica(self):
        mensagem = jobs.montar_mensagem_conclusao({
            "total_no_csv": 12,
            "novos": 0,
            "novos_sem_site": 0,
            "novos_site_ruim": 0,
            "descartados_por_site_ok": 12,
            "descartados_nota_baixa": 0,
            "descartados_sem_telefone": 0,
            "erros_de_linha": 0,
        })
        assert "nenhum lead novo" in mensagem
        assert "12 já têm site bom" in mensagem

    def test_sem_descartes_nao_polui_a_mensagem(self):
        # tudo virou lead: não deve inventar detalhamento vazio
        mensagem = jobs.montar_mensagem_conclusao({
            "total_no_csv": 5,
            "novos": 5,
            "novos_sem_site": 5,
            "novos_site_ruim": 0,
            "descartados_por_site_ok": 0,
            "descartados_nota_baixa": 0,
            "descartados_sem_telefone": 0,
            "erros_de_linha": 0,
        })
        assert "5 lead(s) novo(s)" in mensagem
        assert "Das " not in mensagem


class TestDicaFontePlaces:
    def test_dica_menciona_configuracoes(self):
        assert "Configurações" in jobs.DICA_FONTE_PLACES
        assert "Places" in jobs.DICA_FONTE_PLACES


# ---------------------------------------------------------------------------
# Contadores novos em processar.processar
# ---------------------------------------------------------------------------

class TestContadoresDoFunil:
    @pytest.fixture
    def ambiente(self, tmp_path, monkeypatch):
        monkeypatch.setattr(db, "CAMINHO_BANCO", tmp_path / "leads.db")
        monkeypatch.setattr(processar, "CAMINHO_BANCO", tmp_path / "leads.db")
        monkeypatch.setattr(processar, "PASTA_SAIDAS", tmp_path / "saidas")
        # sem rede: toda candidata vira "sem site"
        monkeypatch.setattr(
            processar, "_verificar_candidata",
            lambda indice, linha: (indice, linha, {
                "site_url": None, "situacao": "sem_site", "problemas": [],
                "checklist": None, "instagram_url": None,
            }),
        )
        conexao = sqlite3.connect(tmp_path / "leads.db")
        processar.preparar_banco(conexao)
        conexao.close()
        return tmp_path

    def _csv(self, pasta, linhas):
        caminho = pasta / "bruto.csv"
        campos = ["input_id", "place_id", "title", "category", "address",
                  "review_rating", "review_count", "phone", "website"]
        with open(caminho, "w", newline="", encoding="utf-8") as arquivo:
            escritor = csv.DictWriter(arquivo, fieldnames=campos)
            escritor.writeheader()
            escritor.writerows(linhas)
        return caminho

    def _linha(self, place_id, nota="4.8", fone="(65) 99999-0001"):
        return {
            "input_id": "q1", "place_id": place_id, "title": f"Empresa {place_id}",
            "category": "Categoria", "address": "Rua X", "review_rating": nota,
            "review_count": "10", "phone": fone, "website": "",
        }

    def test_conta_nota_baixa_e_sem_telefone(self, ambiente):
        caminho = self._csv(ambiente, [
            self._linha("a"),                       # vira lead
            self._linha("b", nota="3.2"),           # nota baixa
            self._linha("c", nota=""),              # sem avaliação
            self._linha("d", fone=""),              # sem telefone
        ])
        contagens = processar.processar(caminho, caminho_queries=None)
        assert contagens["total_no_csv"] == 4
        assert contagens["novos"] == 1
        assert contagens["descartados_nota_baixa"] == 2
        assert contagens["descartados_sem_telefone"] == 1

    def test_mensagem_final_bate_com_o_funil_real(self, ambiente):
        # integração: contadores do processar alimentam a mensagem do jobs
        caminho = self._csv(ambiente, [
            self._linha("a"),
            self._linha("b", nota="2.0"),
        ])
        contagens = processar.processar(caminho, caminho_queries=None)
        mensagem = jobs.montar_mensagem_conclusao(contagens)
        assert "1 lead(s) novo(s)" in mensagem
        assert "1 com nota baixa" in mensagem