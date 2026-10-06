"""Testes de integração das rotas Flask - usam um banco SQLite temporário
(nunca tocam no leads.db real) via app.test_client()."""

import json
import sqlite3
from datetime import datetime, timedelta

import pytest

import app as app_module
import constantes
import db
import jobs
import paths
import processar


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    caminho_banco_teste = tmp_path / "leads_teste.db"
    # todos os módulos de rotas acessam o banco via db.CAMINHO_BANCO (atributo
    # do módulo), então um único patch redireciona o app inteiro pro banco de teste
    monkeypatch.setattr(db, "CAMINHO_BANCO", caminho_banco_teste)

    conexao = sqlite3.connect(caminho_banco_teste)
    processar.preparar_banco(conexao)
    conexao.close()

    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as cliente_teste:
        yield cliente_teste


def inserir_lead(place_id="lead-1", **overrides):
    campos = {
        "place_id": place_id,
        "nome": "Empresa Teste",
        "categoria": "Categoria Teste",
        "endereco": "Endereço Teste",
        "nota": 4.5,
        "num_avaliacoes": 20,
        "whatsapp_link": "https://wa.me/5511999999999",
        "telefone": "5511999999999",
        "query_origem": "nicho teste",
        "status": "novo",
        "visto_em": "2026-01-01",
        "atualizado_em": "2026-01-01T00:00:00",
    }
    campos.update(overrides)
    if "nicho" not in campos or "cidade" not in campos:
        nicho, cidade = processar.extrair_nicho_e_cidade(campos["query_origem"])
        campos.setdefault("nicho", nicho)
        campos.setdefault("cidade", cidade)

    conexao = sqlite3.connect(db.CAMINHO_BANCO)
    conexao.execute(
        """
        INSERT INTO leads (place_id, nome, categoria, endereco, nota, num_avaliacoes,
                            whatsapp_link, telefone, query_origem, nicho, cidade,
                            status, visto_em, atualizado_em)
        VALUES (:place_id, :nome, :categoria, :endereco, :nota, :num_avaliacoes,
                :whatsapp_link, :telefone, :query_origem, :nicho, :cidade,
                :status, :visto_em, :atualizado_em)
        """,
        campos,
    )
    conexao.commit()
    conexao.close()
    return campos


class TestListarLeads:
    def test_lista_vazia_quando_banco_novo(self, cliente):
        resposta = cliente.get("/api/leads")
        assert resposta.status_code == 200
        dados = resposta.get_json()
        assert dados["leads"] == []
        assert dados["tem_mais"] is False

    def test_lista_leads_existentes(self, cliente):
        inserir_lead("lead-1")
        inserir_lead("lead-2")

        resposta = cliente.get("/api/leads")
        assert resposta.status_code == 200
        dados = resposta.get_json()
        assert len(dados["leads"]) == 2

    def test_esconde_ignorados_por_padrao(self, cliente):
        inserir_lead("lead-1", status="novo")
        inserir_lead("lead-2", status="ignorado")

        resposta = cliente.get("/api/leads")
        dados = resposta.get_json()["leads"]
        assert len(dados) == 1
        assert dados[0]["place_id"] == "lead-1"

    def test_filtro_status_ignorado_mostra_so_ignorados(self, cliente):
        inserir_lead("lead-1", status="novo")
        inserir_lead("lead-2", status="ignorado")

        resposta = cliente.get("/api/leads?status=ignorado")
        dados = resposta.get_json()["leads"]
        assert len(dados) == 1
        assert dados[0]["place_id"] == "lead-2"

    def test_paginacao_respeita_limit_e_indica_tem_mais(self, cliente):
        for i in range(5):
            inserir_lead(f"lead-{i}", visto_em=f"2026-01-0{i+1}")

        resposta = cliente.get("/api/leads?limit=2&offset=0")
        dados = resposta.get_json()
        assert len(dados["leads"]) == 2
        assert dados["tem_mais"] is True

        resposta_final = cliente.get("/api/leads?limit=2&offset=4")
        dados_final = resposta_final.get_json()
        assert len(dados_final["leads"]) == 1
        assert dados_final["tem_mais"] is False

    def test_nota_min_invalida_retorna_400(self, cliente):
        resposta = cliente.get("/api/leads?nota_min=abc")
        assert resposta.status_code == 400
        assert "erro" in resposta.get_json()


class TestAtualizarStatus:
    def test_status_valido_atualiza_e_registra_historico(self, cliente):
        inserir_lead("lead-1", status="novo")

        resposta = cliente.post(
            "/api/leads/lead-1/status", json={"status": "contatado"}
        )
        assert resposta.status_code == 200

        historico = cliente.get("/api/leads/lead-1/historico").get_json()
        assert len(historico) == 1
        assert historico[0]["status_anterior"] == "novo"
        assert historico[0]["status_novo"] == "contatado"

    def test_status_invalido_retorna_400(self, cliente):
        inserir_lead("lead-1")
        resposta = cliente.post(
            "/api/leads/lead-1/status", json={"status": "status_que_nao_existe"}
        )
        assert resposta.status_code == 400

    def test_lead_inexistente_retorna_404(self, cliente):
        resposta = cliente.post(
            "/api/leads/nao-existe/status", json={"status": "contatado"}
        )
        assert resposta.status_code == 404


class TestBulkActions:
    def test_bulk_status_atualiza_varios_e_registra_historico(self, cliente):
        inserir_lead("lead-1", status="novo")
        inserir_lead("lead-2", status="novo")
        inserir_lead("lead-3", status="contatado")

        resposta = cliente.post(
            "/api/leads/bulk-status",
            json={"place_ids": ["lead-1", "lead-2"], "status": "contatado"},
        )
        assert resposta.status_code == 200
        assert resposta.get_json()["atualizados"] == 2

        leads = {l["place_id"]: l["status"] for l in cliente.get("/api/leads").get_json()["leads"]}
        assert leads["lead-1"] == "contatado"
        assert leads["lead-2"] == "contatado"
        assert leads["lead-3"] == "contatado"  # já estava, não deve mudar nada

        historico_1 = cliente.get("/api/leads/lead-1/historico").get_json()
        assert historico_1[0]["status_anterior"] == "novo"
        assert historico_1[0]["status_novo"] == "contatado"

    def test_bulk_status_ignora_ids_inexistentes_sem_erro(self, cliente):
        inserir_lead("lead-1", status="novo")
        resposta = cliente.post(
            "/api/leads/bulk-status",
            json={"place_ids": ["lead-1", "nao-existe"], "status": "contatado"},
        )
        assert resposta.status_code == 200
        assert resposta.get_json()["atualizados"] == 1

    def test_bulk_status_sem_ids_retorna_400(self, cliente):
        resposta = cliente.post(
            "/api/leads/bulk-status", json={"place_ids": [], "status": "contatado"}
        )
        assert resposta.status_code == 400

    def test_bulk_status_invalido_retorna_400(self, cliente):
        inserir_lead("lead-1")
        resposta = cliente.post(
            "/api/leads/bulk-status",
            json={"place_ids": ["lead-1"], "status": "nao_existe"},
        )
        assert resposta.status_code == 400

    def test_bulk_ignorar_marca_varios(self, cliente):
        inserir_lead("lead-1", status="novo")
        inserir_lead("lead-2", status="contatado")

        resposta = cliente.post(
            "/api/leads/bulk-ignorar", json={"place_ids": ["lead-1", "lead-2"]}
        )
        assert resposta.status_code == 200
        assert resposta.get_json()["atualizados"] == 2

        ativos = cliente.get("/api/leads").get_json()["leads"]
        assert len(ativos) == 0

        ignorados = cliente.get("/api/leads?status=ignorado").get_json()["leads"]
        assert len(ignorados) == 2

    def test_bulk_ignorar_sem_ids_retorna_400(self, cliente):
        resposta = cliente.post("/api/leads/bulk-ignorar", json={"place_ids": []})
        assert resposta.status_code == 400


class TestExclusaoDefinitiva:
    def test_exclui_lead_ignorado_de_vez(self, cliente):
        inserir_lead("lead-1", status="ignorado")

        resposta = cliente.delete("/api/leads/lead-1")
        assert resposta.status_code == 200

        conexao = sqlite3.connect(db.CAMINHO_BANCO)
        existe = conexao.execute(
            "SELECT 1 FROM leads WHERE place_id = ?", ("lead-1",)
        ).fetchone()
        assert existe is None

    def test_nao_exclui_lead_ativo(self, cliente):
        inserir_lead("lead-1", status="novo")

        resposta = cliente.delete("/api/leads/lead-1")
        assert resposta.status_code == 400

        conexao = sqlite3.connect(db.CAMINHO_BANCO)
        existe = conexao.execute(
            "SELECT 1 FROM leads WHERE place_id = ?", ("lead-1",)
        ).fetchone()
        assert existe is not None

    def test_exclui_lead_inexistente_retorna_404(self, cliente):
        resposta = cliente.delete("/api/leads/nao-existe")
        assert resposta.status_code == 404

    def test_bulk_exclui_so_os_ignorados(self, cliente):
        inserir_lead("lead-1", status="ignorado")
        inserir_lead("lead-2", status="ignorado")
        inserir_lead("lead-3", status="novo")

        resposta = cliente.post(
            "/api/leads/bulk-excluir",
            json={"place_ids": ["lead-1", "lead-2", "lead-3"]},
        )
        assert resposta.status_code == 200
        assert resposta.get_json()["excluidos"] == 2

        conexao = sqlite3.connect(db.CAMINHO_BANCO)
        restantes = {
            r[0] for r in conexao.execute("SELECT place_id FROM leads").fetchall()
        }
        assert restantes == {"lead-3"}

    def test_bulk_exclui_sem_ids_retorna_400(self, cliente):
        resposta = cliente.post("/api/leads/bulk-excluir", json={"place_ids": []})
        assert resposta.status_code == 400


class TestObservacoesETags:
    def test_salva_observacoes(self, cliente):
        inserir_lead("lead-1")
        resposta = cliente.post(
            "/api/leads/lead-1/observacoes", json={"observacoes": "Cliente interessado"}
        )
        assert resposta.status_code == 200

    def test_observacoes_muito_longas_retorna_400(self, cliente):
        inserir_lead("lead-1")
        texto_grande = "a" * (constantes.MAX_CARACTERES_OBSERVACOES + 1)
        resposta = cliente.post(
            "/api/leads/lead-1/observacoes", json={"observacoes": texto_grande}
        )
        assert resposta.status_code == 400

    def test_tags_muito_longas_retorna_400(self, cliente):
        inserir_lead("lead-1")
        tags_grandes = "a" * (constantes.MAX_CARACTERES_TAGS + 1)
        resposta = cliente.post("/api/leads/lead-1/tags", json={"tags": tags_grandes})
        assert resposta.status_code == 400


class TestDispararBusca:
    def test_texto_vazio_retorna_400(self, cliente):
        resposta = cliente.post("/api/buscar", json={"queries": "   "})
        assert resposta.status_code == 400

    def test_excesso_de_linhas_retorna_400(self, cliente):
        linhas = "\n".join(f"nicho teste em cidade {i}" for i in range(60))
        resposta = cliente.post("/api/buscar", json={"queries": linhas})
        assert resposta.status_code == 400

    def test_linha_muito_longa_retorna_400(self, cliente):
        resposta = cliente.post("/api/buscar", json={"queries": "a" * 250})
        assert resposta.status_code == 400

    def test_busca_ja_rodando_retorna_409(self, cliente):
        jobs.estado_busca["rodando"] = True
        try:
            resposta = cliente.post("/api/buscar", json={"queries": "nicho em cidade"})
            assert resposta.status_code == 409
        finally:
            jobs.estado_busca["rodando"] = False


AREA_VALIDA = {"lat": -23.31, "lng": -51.16, "raio_m": 5000, "rotulo": "Londrina - Paraná"}


class TestBuscaPorMapa:
    @pytest.fixture
    def ambiente_busca(self, cliente, tmp_path, monkeypatch):
        """Redireciona o queries.txt pra pasta temporária e captura o disparo da
        thread (que nunca deve rodar de verdade nos testes)."""
        disparos = []
        # o queries.txt é escrito na área de dados (paths.DIR_DADOS)
        monkeypatch.setattr(paths, "DIR_DADOS", tmp_path)
        monkeypatch.setattr(jobs, "iniciar_thread_busca", lambda areas=None: disparos.append(areas))
        return cliente, tmp_path, disparos

    def test_dispara_busca_por_mapa(self, ambiente_busca):
        cliente, tmp_path, disparos = ambiente_busca
        try:
            resposta = cliente.post("/api/buscar", json={
                "nichos": ["clínica de estética", "barbearia"],
                "areas": [AREA_VALIDA],
            })
            assert resposta.status_code == 200

            assert (tmp_path / "queries.txt").read_text(encoding="utf-8") == "clínica de estética\nbarbearia\n"
            assert len(disparos) == 1
            assert disparos[0] == [
                {"lat": -23.31, "lng": -51.16, "raio_m": 5000, "rotulo": "Londrina - Paraná"}
            ]
        finally:
            jobs.liberar_busca()

    def test_rotulo_ausente_cai_nas_coordenadas(self, ambiente_busca):
        cliente, _tmp_path, disparos = ambiente_busca
        try:
            resposta = cliente.post("/api/buscar", json={
                "nichos": ["barbearia"],
                "areas": [{"lat": -23.31, "lng": -51.16, "raio_m": 2000}],
            })
            assert resposta.status_code == 200
            assert disparos[0][0]["rotulo"] == "-23.3100, -51.1600"
        finally:
            jobs.liberar_busca()

    def test_sem_nichos_retorna_400(self, ambiente_busca):
        cliente, _, _ = ambiente_busca
        resposta = cliente.post("/api/buscar", json={"nichos": [], "areas": [AREA_VALIDA]})
        assert resposta.status_code == 400

    def test_nichos_so_com_espacos_retorna_400(self, ambiente_busca):
        cliente, _, _ = ambiente_busca
        resposta = cliente.post("/api/buscar", json={"nichos": ["   ", ""], "areas": [AREA_VALIDA]})
        assert resposta.status_code == 400

    def test_sem_areas_retorna_400(self, ambiente_busca):
        cliente, _, _ = ambiente_busca
        resposta = cliente.post("/api/buscar", json={"nichos": ["barbearia"], "areas": []})
        assert resposta.status_code == 400

    def test_excesso_de_areas_retorna_400(self, ambiente_busca):
        cliente, _, _ = ambiente_busca
        resposta = cliente.post("/api/buscar", json={
            "nichos": ["barbearia"],
            "areas": [AREA_VALIDA] * 6,
        })
        assert resposta.status_code == 400

    def test_raio_fora_dos_limites_retorna_400(self, ambiente_busca):
        cliente, _, _ = ambiente_busca
        for raio in (100, 100_000):
            resposta = cliente.post("/api/buscar", json={
                "nichos": ["barbearia"],
                "areas": [{**AREA_VALIDA, "raio_m": raio}],
            })
            assert resposta.status_code == 400

    def test_coordenadas_invalidas_retorna_400(self, ambiente_busca):
        cliente, _, _ = ambiente_busca
        for lat, lng in ((-91, -51.16), (-23.31, 181), ("abc", -51.16)):
            resposta = cliente.post("/api/buscar", json={
                "nichos": ["barbearia"],
                "areas": [{"lat": lat, "lng": lng, "raio_m": 5000}],
            })
            assert resposta.status_code == 400

    def test_busca_por_mapa_com_busca_rodando_retorna_409(self, ambiente_busca):
        cliente, _, _ = ambiente_busca
        jobs.estado_busca["rodando"] = True
        try:
            resposta = cliente.post("/api/buscar", json={
                "nichos": ["barbearia"], "areas": [AREA_VALIDA],
            })
            assert resposta.status_code == 409
        finally:
            jobs.estado_busca["rodando"] = False


class TestZoomParaRaio:
    def test_raios_comuns(self):
        assert jobs.zoom_para_raio(1000) == 15
        assert jobs.zoom_para_raio(5000) == 13
        assert jobs.zoom_para_raio(10000) == 12
        assert jobs.zoom_para_raio(50000) == 9

    def test_limites(self):
        assert jobs.zoom_para_raio(100) == 16  # raio mínimo tratado como 500m
        assert jobs.zoom_para_raio(10_000_000) == 8  # nunca abaixo do zoom 8


class TestMetricas:
    def test_banco_vazio(self, cliente):
        resposta = cliente.get("/api/metricas")
        dados = resposta.get_json()
        assert dados["total"] == 0
        assert dados["taxa_conversao"] == 0

    def test_contagens_corretas(self, cliente):
        inserir_lead("lead-1", status="novo")
        inserir_lead("lead-2", status="contatado")
        inserir_lead("lead-3", status="fechou")
        inserir_lead("lead-4", status="ignorado")  # não deve contar

        resposta = cliente.get("/api/metricas")
        dados = resposta.get_json()
        assert dados["total"] == 3
        assert dados["por_status"]["novo"] == 1
        assert dados["por_status"]["contatado"] == 1
        assert dados["por_status"]["fechou"] == 1
        assert "ignorado" not in dados["por_status"]
        assert dados["taxa_conversao"] == round(100 / 3, 1)

    def test_lembretes_hoje_conta_vencidos_e_hoje(self, cliente):
        hoje = datetime.now().strftime("%Y-%m-%d")
        ontem = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        amanha = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        inserir_lead("lead-1", proximo_followup=hoje)
        inserir_lead("lead-2", proximo_followup=ontem)
        inserir_lead("lead-3", proximo_followup=amanha)

        # a coluna proximo_followup é aditiva (migração), inserir_lead não a define
        # por padrão - setamos direto via UPDATE pra simular o dado real.
        conexao = sqlite3.connect(db.CAMINHO_BANCO)
        conexao.execute("UPDATE leads SET proximo_followup = ? WHERE place_id = ?", (hoje, "lead-1"))
        conexao.execute("UPDATE leads SET proximo_followup = ? WHERE place_id = ?", (ontem, "lead-2"))
        conexao.execute("UPDATE leads SET proximo_followup = ? WHERE place_id = ?", (amanha, "lead-3"))
        conexao.commit()
        conexao.close()

        resposta = cliente.get("/api/metricas")
        dados = resposta.get_json()
        assert dados["lembretes_hoje"] == 2  # hoje + ontem (vencido), não amanhã


class TestAnalytics:
    def test_funil_banco_vazio(self, cliente):
        resposta = cliente.get("/api/analytics/funil")
        dados = resposta.get_json()
        assert dados["estagios"] == [
            {"status": "novo", "total": 0},
            {"status": "contatado", "total": 0},
            {"status": "respondeu", "total": 0},
            {"status": "fechou", "total": 0},
        ]

    def test_funil_conta_progressao_por_historico(self, cliente):
        inserir_lead("lead-1", status="novo")
        inserir_lead("lead-2", status="novo")
        inserir_lead("lead-3", status="novo")

        # lead-2 avança até "respondeu", lead-3 avança até "fechou" -
        # cada avanço deve contar em todos os estágios anteriores também.
        cliente.post("/api/leads/lead-2/status", json={"status": "contatado"})
        cliente.post("/api/leads/lead-2/status", json={"status": "respondeu"})
        cliente.post("/api/leads/lead-3/status", json={"status": "contatado"})
        cliente.post("/api/leads/lead-3/status", json={"status": "respondeu"})
        cliente.post("/api/leads/lead-3/status", json={"status": "fechou"})

        dados = cliente.get("/api/analytics/funil").get_json()
        por_estagio = {e["status"]: e["total"] for e in dados["estagios"]}
        assert por_estagio["novo"] == 3       # todos passaram por "novo"
        assert por_estagio["contatado"] == 2  # lead-2 e lead-3
        assert por_estagio["respondeu"] == 2  # lead-2 e lead-3
        assert por_estagio["fechou"] == 1     # só lead-3

    def test_funil_ignora_leads_ignorados(self, cliente):
        inserir_lead("lead-1", status="novo")
        inserir_lead("lead-2", status="ignorado")

        dados = cliente.get("/api/analytics/funil").get_json()
        por_estagio = {e["status"]: e["total"] for e in dados["estagios"]}
        assert por_estagio["novo"] == 1

    def test_por_nicho_banco_vazio(self, cliente):
        resposta = cliente.get("/api/analytics/por-nicho")
        assert resposta.get_json() == {"nichos": []}

    def test_por_nicho_agrega_e_calcula_conversao(self, cliente):
        inserir_lead("lead-1", query_origem="clínica de estética em Londrina", status="fechou")
        inserir_lead("lead-2", query_origem="clínica de estética em Maringá", status="novo")
        inserir_lead("lead-3", query_origem="corretor de imóveis em Londrina", status="novo")
        inserir_lead("lead-4", query_origem="corretor de imóveis em Londrina", status="ignorado")

        dados = cliente.get("/api/analytics/por-nicho").get_json()["nichos"]
        por_nicho = {n["nicho"]: n for n in dados}

        # duas cidades diferentes do mesmo nicho devem ser agregadas juntas
        assert por_nicho["clínica de estética"]["total"] == 2
        assert por_nicho["clínica de estética"]["fechados"] == 1
        assert por_nicho["clínica de estética"]["taxa_conversao"] == 50.0

        assert por_nicho["corretor de imóveis"]["total"] == 1  # ignorado não conta


class TestLimiteBulk:
    def test_bulk_status_acima_do_limite_retorna_400(self, cliente):
        ids = [f"lead-{i}" for i in range(501)]
        resposta = cliente.post("/api/leads/bulk-status", json={"place_ids": ids, "status": "contatado"})
        assert resposta.status_code == 400
        assert "500" in resposta.get_json()["erro"]

    def test_bulk_excluir_acima_do_limite_retorna_400(self, cliente):
        ids = [f"lead-{i}" for i in range(501)]
        resposta = cliente.post("/api/leads/bulk-excluir", json={"place_ids": ids})
        assert resposta.status_code == 400

    def test_bulk_no_limite_exato_passa(self, cliente):
        inserir_lead("lead-0", status="novo")
        ids = [f"lead-{i}" for i in range(500)]  # exatamente o limite
        resposta = cliente.post("/api/leads/bulk-status", json={"place_ids": ids, "status": "contatado"})
        assert resposta.status_code == 200
