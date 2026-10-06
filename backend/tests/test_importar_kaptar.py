"""Testes do importador do Kaptar: parsing do CSV (os dois formatos de export
+ o formato simples), dedupe e atualização de lead existente por telefone.
"""

import sqlite3
import sys
from pathlib import Path

import pytest
from flask import Flask

sys.path.insert(0, str(Path(__file__).parent.parent))

import db
import importar_kaptar
import processar
import rotas_importar

# O app "de verdade" (app.py) não registra rotas_importar.bp ainda - fica por
# conta do engenheiro líder no startup real. Testar num Flask isolado (em vez
# de registrar em cima do app_module.app compartilhado por todos os arquivos
# de teste) evita dois problemas: (1) o Flask recusa registrar blueprint depois
# que o app já respondeu a primeira requisição ("can no longer be called"),
# então qualquer outro arquivo de teste que já tenha usado app_module.app
# antes deste rodar quebraria a importação da rota; (2) registrar no app
# compartilhado ficaria pra trás depois que outro processo de teste (rodando
# em paralelo, nesta mesma suíte) também tentasse - um Flask próprio, só com
# o blueprint que este arquivo testa, não tem esse acoplamento com mais nada.
def _montar_app_teste():
    app_teste = Flask(__name__)
    app_teste.register_blueprint(rotas_importar.bp)
    app_teste.config["TESTING"] = True
    return app_teste


# ---------------------------------------------------------------------------
# CSVs de amostra (escritos aqui dentro, como pedido - nada de fixture externa)
# ---------------------------------------------------------------------------

# Formato "leads" do Kaptar: cabeçalho com BOM, separador ";", campo com
# vírgula dentro de aspas (Resumo).
CSV_LEADS_KAPTAR = (
    "﻿"
    "Nome;Nicho;Telefone;WhatsApp provável;Responsável;Resumo;Score\r\n"
    'Clínica Sorriso;Odontologia;(41) 98999-0011;Sim;Dra. Ana Souza;"Atende bem, mas sem redes sociais";72\r\n'
    "Estética Vitá;Estética;41984561122;Não;Bruno;Site fora do ar;58\r\n"
)

# Formato "ativos" do Kaptar: separador ",", sem BOM. O texto do /instalar só
# cita as colunas que distinguem este export do formato "leads" (Tem site,
# Tem Instagram, Status, Tipo); telefone entra do mesmo jeito nos dois exports
# reais do Kaptar, senão a lista não serviria pra disparo nenhum.
CSV_ATIVOS_KAPTAR = (
    "Nome,Categoria,Telefone,Tem site,Tem Instagram,Status,Tipo\n"
    "Barbearia do Zé,Beleza,41991112222,Não,Sim,Ativo,Prospecção\n"
    "Auto Center Norte,Automotivo,41988883333,Sim,Não,Ativo,Cliente\n"
)

# Formato simples: uma linha por contato, "Nome, telefone".
CSV_SIMPLES = (
    "Clínica Odonto Feliz, 41999990000\n"
    "Consultório Dra. Paula, 41 3222-0011\n"  # fixo (sem nono dígito)
)

CSV_COM_DUPLICATA = (
    "Nome,Telefone\n"
    "Empresa A,41999990000\n"
    "Empresa A de novo,(41) 99999-0000\n"  # mesmo número, variação de máscara
)

CSV_TELEFONE_INVALIDO = (
    "Nome,Telefone\n"
    "Sem numero,123\n"
    "Boa,41999990000\n"
)


@pytest.fixture
def banco(tmp_path, monkeypatch):
    caminho = tmp_path / "leads_teste.db"
    monkeypatch.setattr(db, "CAMINHO_BANCO", caminho)
    conexao = sqlite3.connect(caminho)
    processar.preparar_banco(conexao)
    conexao.close()
    return caminho


@pytest.fixture
def conexao(banco):
    con = sqlite3.connect(banco)
    con.row_factory = sqlite3.Row
    yield con
    con.close()


@pytest.fixture
def cliente(banco):
    app_teste = _montar_app_teste()
    with app_teste.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# Normalização de número
# ---------------------------------------------------------------------------


class TestNormalizarNumero:
    def test_celular_com_mascara_ganha_ddi(self):
        assert importar_kaptar.normalizar_numero("(41) 98999-0011") == "5541989990011"

    def test_ja_com_ddi_mantem(self):
        assert importar_kaptar.normalizar_numero("5541989990011") == "5541989990011"

    def test_fixo_sem_nono_digito(self):
        assert importar_kaptar.normalizar_numero("41 3222-0011") == "554132220011"

    def test_numero_curto_invalido(self):
        assert importar_kaptar.normalizar_numero("123") is None

    def test_vazio_invalido(self):
        assert importar_kaptar.normalizar_numero("") is None
        assert importar_kaptar.normalizar_numero(None) is None


class TestECelular:
    def test_celular_com_nono_digito(self):
        assert importar_kaptar._e_celular("5541989990011") is True

    def test_fixo_sem_nono_digito(self):
        assert importar_kaptar._e_celular("554132220011") is False


# ---------------------------------------------------------------------------
# ler_csv - separador, aspas, BOM
# ---------------------------------------------------------------------------


class TestLerCsv:
    def test_detecta_separador_ponto_e_virgula_e_remove_bom(self):
        linhas = importar_kaptar.ler_csv(CSV_LEADS_KAPTAR)
        assert linhas[0][0] == "Nome"  # BOM não gruda no primeiro campo
        assert linhas[0] == ["Nome", "Nicho", "Telefone", "WhatsApp provável", "Responsável", "Resumo", "Score"]

    def test_campo_com_virgula_dentro_de_aspas_nao_quebra_a_linha(self):
        linhas = importar_kaptar.ler_csv(CSV_LEADS_KAPTAR)
        linha_ana = linhas[1]
        assert linha_ana[5] == "Atende bem, mas sem redes sociais"

    def test_detecta_separador_virgula(self):
        linhas = importar_kaptar.ler_csv(CSV_ATIVOS_KAPTAR)
        assert linhas[0] == ["Nome", "Categoria", "Telefone", "Tem site", "Tem Instagram", "Status", "Tipo"]

    def test_texto_vazio_nao_quebra(self):
        assert importar_kaptar.ler_csv("") == []
        assert importar_kaptar.ler_csv(None) == []


# ---------------------------------------------------------------------------
# ler_contatos - os três formatos + dedupe + inválidos
# ---------------------------------------------------------------------------


class TestLerContatosFormatoLeads:
    def test_le_os_dois_contatos(self):
        contatos, invalidos = importar_kaptar.ler_contatos(CSV_LEADS_KAPTAR)
        assert not invalidos
        assert len(contatos) == 2

    def test_campos_mapeados_corretamente(self):
        contatos, _ = importar_kaptar.ler_contatos(CSV_LEADS_KAPTAR)
        ana = contatos[0]
        assert ana["nome"] == "Clínica Sorriso"
        assert ana["nicho"] == "Odontologia"
        assert ana["numero"] == "5541989990011"
        assert ana["responsavel"] == "Dra. Ana Souza"
        assert ana["primeiro_nome"] == "Ana"  # "Dra." é removido
        assert ana["resumo"] == "Atende bem, mas sem redes sociais"
        assert ana["score_num"] == 72.0
        assert "tem_site" not in ana  # coluna não veio nesse export

    def test_tem_site_explicito_no_formato_ativos(self):
        contatos, _ = importar_kaptar.ler_contatos(CSV_ATIVOS_KAPTAR)
        barbearia, auto_center = contatos
        assert barbearia["tem_site"] == "Não"
        assert barbearia["tem_site_bool"] is False
        assert barbearia["tem_instagram"] == "Sim"
        assert barbearia["tem_instagram_bool"] is True
        assert auto_center["tem_site"] == "Sim"
        assert auto_center["tem_site_bool"] is True
        assert auto_center["tem_instagram_bool"] is False


class TestLerContatosFormatoSimples:
    def test_le_nome_e_telefone(self):
        contatos, invalidos = importar_kaptar.ler_contatos(CSV_SIMPLES)
        assert not invalidos
        assert len(contatos) == 2
        assert contatos[0]["nome"] == "Clínica Odonto Feliz"
        assert contatos[0]["numero"] == "5541999990000"

    def test_fixo_nao_e_marcado_como_whatsapp_provavel_por_padrao(self):
        contatos, _ = importar_kaptar.ler_contatos(CSV_SIMPLES)
        fixo = contatos[1]
        assert fixo["whatsapp_provavel_bool"] is False  # sem nono dígito = não é celular

    def test_so_numero_sem_nome(self):
        contatos, invalidos = importar_kaptar.ler_contatos("41999990000")
        assert not invalidos
        assert contatos[0]["nome"] == ""
        assert contatos[0]["numero"] == "5541999990000"


class TestLerContatosDuplicataEInvalidos:
    def test_duplicata_por_variacao_de_mascara_e_descartada(self):
        contatos, invalidos = importar_kaptar.ler_contatos(CSV_COM_DUPLICATA)
        assert len(contatos) == 1
        assert len(invalidos) == 1
        assert invalidos[0]["motivo"] == "número repetido na lista"

    def test_telefone_invalido_e_contado(self):
        contatos, invalidos = importar_kaptar.ler_contatos(CSV_TELEFONE_INVALIDO)
        assert len(contatos) == 1
        assert len(invalidos) == 1
        assert invalidos[0]["motivo"] == "telefone inválido"

    def test_arquivo_vazio_nao_quebra(self):
        contatos, invalidos = importar_kaptar.ler_contatos("")
        assert contatos == []
        assert invalidos == []


# ---------------------------------------------------------------------------
# preparar() - migração de leads.origem
# ---------------------------------------------------------------------------


class TestPreparar:
    def test_adiciona_coluna_origem_idempotente(self, conexao):
        importar_kaptar.preparar(conexao)
        importar_kaptar.preparar(conexao)  # roda de novo, não pode quebrar
        colunas = {linha[1] for linha in conexao.execute("PRAGMA table_info(leads)")}
        assert "origem" in colunas

    def test_backfill_maps_para_leads_antigos(self, conexao):
        conexao.execute(
            "INSERT INTO leads (place_id, nome, status, visto_em, atualizado_em) "
            "VALUES ('antigo-1', 'Empresa Antiga', 'novo', '2026-01-01', '2026-01-01')"
        )
        conexao.commit()
        importar_kaptar.preparar(conexao)
        origem = conexao.execute("SELECT origem FROM leads WHERE place_id = 'antigo-1'").fetchone()["origem"]
        assert origem == "maps"


# ---------------------------------------------------------------------------
# importar_leads_csv - via rota HTTP (cobre schema, dedupe contra o banco, etc)
# ---------------------------------------------------------------------------


class TestImportarKaptarRota:
    def test_importa_formato_leads(self, cliente):
        resposta = cliente.post("/api/importar/kaptar", json={"conteudo": CSV_LEADS_KAPTAR})
        dados = resposta.get_json()
        assert resposta.status_code == 200
        assert dados["importados"] == 2
        assert dados["atualizados"] == 0
        assert dados["descartados"] == {}

    def test_lead_importado_tem_origem_kaptar_e_status_novo(self, cliente, conexao):
        cliente.post("/api/importar/kaptar", json={"conteudo": CSV_LEADS_KAPTAR})
        lead = conexao.execute(
            "SELECT * FROM leads WHERE place_id = 'kaptar:41989990011'"
        ).fetchone()
        assert lead is not None
        assert lead["origem"] == "kaptar"
        assert lead["status"] == "novo"
        assert lead["nicho"] == "Odontologia"
        assert "Atende bem" in lead["observacoes"]
        assert "Dra. Ana Souza" in lead["observacoes"]

    def test_tem_site_nao_vira_sem_site_e_sim_vira_site_ok(self, cliente, conexao):
        cliente.post("/api/importar/kaptar", json={"conteudo": CSV_ATIVOS_KAPTAR})
        barbearia = conexao.execute(
            "SELECT * FROM leads WHERE nome = 'Barbearia do Zé'"
        ).fetchone()
        auto_center = conexao.execute(
            "SELECT * FROM leads WHERE nome = 'Auto Center Norte'"
        ).fetchone()
        assert barbearia["site_status"] == "sem_site"
        assert auto_center["site_status"] == "site_ok"

    def test_tem_instagram_sim_vira_tag_sem_inventar_url(self, cliente, conexao):
        cliente.post("/api/importar/kaptar", json={"conteudo": CSV_ATIVOS_KAPTAR})
        barbearia = conexao.execute(
            "SELECT * FROM leads WHERE nome = 'Barbearia do Zé'"
        ).fetchone()
        assert barbearia["instagram_url"] is None
        assert "instagram" in (barbearia["tags"] or "").lower()

    def test_formato_simples_usa_nicho_e_cidade_padrao(self, cliente, conexao):
        cliente.post(
            "/api/importar/kaptar",
            json={"conteudo": CSV_SIMPLES, "nicho_padrao": "clínica odontológica", "cidade_padrao": "Curitiba"},
        )
        lead = conexao.execute(
            "SELECT * FROM leads WHERE place_id = 'kaptar:41999990000'"
        ).fetchone()
        assert lead["nicho"] == "clínica odontológica"
        assert lead["cidade"] == "Curitiba"

    def test_dedupe_entre_linhas_do_mesmo_csv(self, cliente):
        dados = cliente.post("/api/importar/kaptar", json={"conteudo": CSV_COM_DUPLICATA}).get_json()
        assert dados["importados"] == 1
        assert dados["descartados"] == {"número repetido na lista": 1}

    def test_telefone_invalido_e_contado_e_nao_importado(self, cliente):
        dados = cliente.post("/api/importar/kaptar", json={"conteudo": CSV_TELEFONE_INVALIDO}).get_json()
        assert dados["importados"] == 1
        assert dados["descartados"] == {"telefone inválido": 1}

    def test_lead_ja_existente_e_atualizado_nao_duplicado(self, cliente, conexao):
        # lead já capturado pelo Maps antes, com telefone sem o nono dígito
        # (histórico antigo) e sem nicho preenchido
        conexao.execute(
            "INSERT INTO leads (place_id, nome, telefone, whatsapp_link, status, "
            "site_status, visto_em, atualizado_em) "
            "VALUES ('maps-xyz', 'Clínica Sorriso', '4189990011', 'https://wa.me/5541989990011', "
            "'contatado', 'sem_site', '2026-01-01', '2026-01-01')"
        )
        conexao.commit()

        dados = cliente.post("/api/importar/kaptar", json={"conteudo": CSV_LEADS_KAPTAR}).get_json()
        assert dados["atualizados"] >= 1
        assert dados["importados"] == 1  # só a Estética Vitá é nova

        lead = conexao.execute("SELECT * FROM leads WHERE place_id = 'maps-xyz'").fetchone()
        assert lead is not None
        assert lead["status"] == "contatado"  # não regride o funil
        assert lead["nicho"] == "Odontologia"  # preencheu o que faltava
        assert lead["site_status"] == "sem_site"  # não sobrescreveu o que já tinha

    def test_place_id_sintetico_nunca_colide_com_maps(self, cliente, conexao):
        cliente.post("/api/importar/kaptar", json={"conteudo": CSV_SIMPLES})
        lead = conexao.execute(
            "SELECT place_id FROM leads WHERE place_id = 'kaptar:41999990000'"
        ).fetchone()
        assert lead is not None

    def test_conteudo_vazio_retorna_400(self, cliente):
        assert cliente.post("/api/importar/kaptar", json={"conteudo": ""}).status_code == 400
        assert cliente.post("/api/importar/kaptar", json={}).status_code == 400

    def test_reimportar_o_mesmo_csv_nao_duplica(self, cliente):
        cliente.post("/api/importar/kaptar", json={"conteudo": CSV_LEADS_KAPTAR})
        dados = cliente.post("/api/importar/kaptar", json={"conteudo": CSV_LEADS_KAPTAR}).get_json()
        assert dados["importados"] == 0
        assert dados["atualizados"] == 2
