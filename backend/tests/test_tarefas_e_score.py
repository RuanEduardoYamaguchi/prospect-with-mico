"""Testes do score de leads (ordenação da fila de abordagem) e da rota
/api/tarefas-hoje (mesa de trabalho do dia)."""

import sqlite3
from datetime import datetime, timedelta

import pytest

import app as app_module
import db
import processar
import rotas_leads
from rotas_leads import calcular_score


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    caminho_banco_teste = tmp_path / "leads_teste.db"
    monkeypatch.setattr(db, "CAMINHO_BANCO", caminho_banco_teste)

    conexao = sqlite3.connect(caminho_banco_teste)
    processar.preparar_banco(conexao)
    conexao.close()

    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as cliente_teste:
        yield cliente_teste


def inserir_lead(place_id, **overrides):
    campos = {
        "place_id": place_id,
        "nome": f"Empresa {place_id}",
        "categoria": "Categoria",
        "endereco": "Endereço",
        "nota": 4.5,
        "num_avaliacoes": 20,
        "whatsapp_link": "https://wa.me/5511999999999",
        "telefone": "5511999999999",
        "query_origem": "nicho em cidade",
        "nicho": "nicho",
        "cidade": "cidade",
        "status": "novo",
        "site_status": "sem_site",
        "site_problemas": None,
        "proximo_followup": None,
        "mensagem_gerada": None,
        "visto_em": "2026-01-01",
        "atualizado_em": "2026-01-01T00:00:00",
    }
    campos.update(overrides)

    conexao = sqlite3.connect(db.CAMINHO_BANCO)
    conexao.execute(
        """
        INSERT INTO leads (place_id, nome, categoria, endereco, nota, num_avaliacoes,
                           whatsapp_link, telefone, query_origem, nicho, cidade, status,
                           site_status, site_problemas, proximo_followup, mensagem_gerada,
                           visto_em, atualizado_em)
        VALUES (:place_id, :nome, :categoria, :endereco, :nota, :num_avaliacoes,
                :whatsapp_link, :telefone, :query_origem, :nicho, :cidade, :status,
                :site_status, :site_problemas, :proximo_followup, :mensagem_gerada,
                :visto_em, :atualizado_em)
        """,
        campos,
    )
    conexao.commit()
    conexao.close()


def inserir_lead_instagram(username, **overrides):
    conexao = sqlite3.connect(db.CAMINHO_BANCO)
    cursor = conexao.execute(
        "INSERT INTO instagram_posts (post_url, criado_em, etapa) VALUES ('https://www.instagram.com/p/X/', '2026-01-01', 'concluido')"
    )
    post_id = cursor.lastrowid
    campos = {
        "post_id": post_id,
        "username": username,
        "status": "contatado",
        "proximo_followup": None,
        "sugestao_dm": None,
        "follow_ups_enviados": 0,
        "atualizado_em": "2026-01-01T00:00:00",
    }
    campos.update(overrides)
    conexao.execute(
        """
        INSERT INTO instagram_leads (post_id, username, status, proximo_followup,
                                     sugestao_dm, follow_ups_enviados, atualizado_em)
        VALUES (:post_id, :username, :status, :proximo_followup, :sugestao_dm,
                :follow_ups_enviados, :atualizado_em)
        """,
        campos,
    )
    conexao.commit()
    conexao.close()


class TestCalcularScore:
    def test_lead_perfeito_sem_site(self):
        # nota 5.0 (40) + 100+ avaliações (30) + sem site (30) = 100
        assert calcular_score(5.0, 150, "sem_site") == 100

    def test_lead_site_ruim_pontua_menos_que_sem_site(self):
        assert calcular_score(5.0, 150, "site_ruim") == 92
        assert calcular_score(5.0, 150, "site_ruim") < calcular_score(5.0, 150, "sem_site")

    def test_nota_minima_zera_pontos_de_nota(self):
        assert calcular_score(4.0, 0, "sem_site") == 30

    def test_nota_nula_nao_explode(self):
        assert calcular_score(None, None, None) == 30


class TestOrdenacaoPorScore:
    def test_ordenar_por_score_poe_o_mais_quente_primeiro(self, cliente):
        inserir_lead("morno", nota=4.1, num_avaliacoes=5, visto_em="2026-07-17")
        inserir_lead("quente", nota=5.0, num_avaliacoes=200, visto_em="2026-01-01")

        # ordenação padrão: mais recente primeiro (morno)
        padrao = cliente.get("/api/leads").get_json()["leads"]
        assert [l["place_id"] for l in padrao] == ["morno", "quente"]

        # por score: o quente vem primeiro, mesmo sendo mais antigo
        por_score = cliente.get("/api/leads?ordenar=score").get_json()["leads"]
        assert [l["place_id"] for l in por_score] == ["quente", "morno"]

    def test_resposta_inclui_score_e_campos_de_site(self, cliente):
        inserir_lead("lead-1", site_status="site_ruim", site_problemas="sem HTTPS")

        lead = cliente.get("/api/leads").get_json()["leads"][0]
        # a rota enriquece o score com os campos reais do lead (site_problemas,
        # instagram_url, nicho) - a chamada de comparação precisa dos mesmos,
        # senão o bônus de "poucas avaliações + nota alta" e o de "sem
        # instagram" (que o lead de teste tem os dois) ficam de fora
        assert lead["score"] == calcular_score(
            4.5, 20, "site_ruim", site_problemas="sem HTTPS", instagram_url=None, nicho="nicho"
        )
        assert lead["site_status"] == "site_ruim"
        assert lead["site_problemas"] == "sem HTTPS"

    def test_ordenar_invalido_retorna_400(self, cliente):
        assert cliente.get("/api/leads?ordenar=alfabetica").status_code == 400

    def test_score_site_ok_e_o_mais_baixo(self):
        assert calcular_score(5.0, 150, "site_ok") == 80
        assert calcular_score(5.0, 150, "site_ok") < calcular_score(5.0, 150, "site_ruim")


class TestScorePesosNovos:
    """Os ajustes do score pra quem vende serviço digital (site, Instagram,
    GMB) pra negócio local. Cada teste isola um ajuste, comparando com/sem o gatilho
    pra não depender dos valores exatos de pesos_score.json mudarem no
    futuro (menos o teste de clamp, que usa pesos extremos de propósito)."""

    def test_bonus_construtor_generico(self):
        sem_construtor = calcular_score(4.0, 0, "site_ruim")
        com_construtor = calcular_score(4.0, 0, "site_ruim", site_problemas="feito em construtor pronto (Wix)")
        assert com_construtor == sem_construtor + rotas_leads.PESOS_SCORE["bonus_construtor_generico"]

    def test_construtor_generico_e_case_insensitive_dentro_do_texto(self):
        # site_problemas real é "; ".join(problemas) - o trecho pode vir no meio
        assert calcular_score(4.0, 0, "site_ruim", site_problemas="sem HTTPS; feito em construtor pronto (Canva)") \
            == calcular_score(4.0, 0, "site_ruim", site_problemas="feito em construtor pronto (Wix)")

    def test_bonus_nota_alta_poucas_avaliacoes_no_limite(self):
        no_limite = calcular_score(4.5, 60, "sem_site")
        um_a_mais = calcular_score(4.5, 61, "sem_site")
        # sem o bônus, 61 avaliações vale mais em pontos_avaliacoes que 60 -
        # mesmo assim o total cai, porque o bônus (10) pesa mais que a
        # diferença de 0.3 ponto de uma avaliação a mais
        assert no_limite > um_a_mais
        assert no_limite == um_a_mais + rotas_leads.PESOS_SCORE["bonus_avaliacao_alta_poucas_avaliacoes"] - round(0.3)

    def test_bonus_nota_alta_exige_a_nota_minima(self):
        sem_bonus = calcular_score(4.4, 10, "sem_site")  # nota abaixo do mínimo padrão (4.5)
        com_bonus = calcular_score(4.5, 10, "sem_site")
        assert com_bonus > sem_bonus

    def test_bonus_sem_instagram_so_aplica_quando_informado(self):
        sem_info = calcular_score(4.0, 0, "sem_site")  # chamador não passou instagram_url
        com_instagram = calcular_score(4.0, 0, "sem_site", instagram_url="https://instagram.com/clinica")
        sem_instagram = calcular_score(4.0, 0, "sem_site", instagram_url=None)
        assert sem_info == com_instagram  # sem informação = sem bônus, igual a "tem"
        assert sem_instagram == com_instagram + rotas_leads.PESOS_SCORE["bonus_sem_instagram"]

    def test_penalidade_muitas_avaliacoes(self):
        poucas = calcular_score(4.0, 1000, "sem_site")  # no limite, ainda não penaliza
        muitas = calcular_score(4.0, 1500, "sem_site")  # acima de 1000, penaliza
        assert muitas == poucas - rotas_leads.PESOS_SCORE["penalidade_muitas_avaliacoes"]

    def test_bonus_nicho_alvo_bate_por_substring_case_insensitive(self):
        pesos = {**rotas_leads.PESOS_SCORE, "bonus_nicho_alvo": 12, "nichos_alvo": ["odonto"]}
        sem_nicho_alvo = calcular_score(4.0, 0, "sem_site", nicho="salão de beleza", pesos=pesos)
        com_nicho_alvo = calcular_score(4.0, 0, "sem_site", nicho="ODONTOLOGIA GERAL", pesos=pesos)
        assert com_nicho_alvo == sem_nicho_alvo + 12

    def test_bonus_nicho_alvo_nao_bate_nicho_qualquer(self):
        pesos = {**rotas_leads.PESOS_SCORE, "bonus_nicho_alvo": 12, "nichos_alvo": ["odonto"]}
        assert calcular_score(4.0, 0, "sem_site", nicho="pet shop", pesos=pesos) == calcular_score(4.0, 0, "sem_site", pesos=pesos)

    def test_sem_nichos_alvo_configurados_nenhum_nicho_ganha_bonus(self):
        pesos = {**rotas_leads.PESOS_SCORE, "bonus_nicho_alvo": 12, "nichos_alvo": []}
        assert calcular_score(4.0, 0, "sem_site", nicho="odontologia", pesos=pesos) == calcular_score(4.0, 0, "sem_site", pesos=pesos)

    def test_clamp_nunca_fica_negativo(self):
        pesos_extremos = {**rotas_leads.PESOS_SCORE, "penalidade_muitas_avaliacoes": 500}
        assert calcular_score(4.0, 2000, "sem_site", pesos=pesos_extremos) == 0

    def test_clamp_nunca_passa_de_100(self):
        pesos_extremos = {**rotas_leads.PESOS_SCORE, "bonus_nicho_alvo": 500, "nichos_alvo": ["odonto"]}
        assert calcular_score(5.0, 50, "sem_site", nicho="odonto", pesos=pesos_extremos) == 100

    def test_pesos_carregados_do_json_batem_com_o_arquivo_do_repo(self):
        # pesos_score.json do repo hoje espelha os padrões - checa que o
        # carregamento real (não os padrões embutidos) está lendo o arquivo
        assert rotas_leads.PESOS_SCORE["bonus_construtor_generico"] == 8
        assert rotas_leads.PESOS_SCORE["nichos_alvo"] == []

    def test_arquivo_ausente_cai_no_padrao(self, tmp_path):
        pesos = rotas_leads._carregar_pesos_score(tmp_path / "nao-existe.json")
        assert pesos == rotas_leads.PESOS_SCORE_PADRAO

    def test_arquivo_invalido_cai_no_padrao(self, tmp_path):
        caminho = tmp_path / "pesos_score.json"
        caminho.write_text("isso não é um JSON válido {", encoding="utf-8")
        pesos = rotas_leads._carregar_pesos_score(caminho)
        assert pesos == rotas_leads.PESOS_SCORE_PADRAO

    def test_arquivo_nao_e_objeto_cai_no_padrao(self, tmp_path):
        caminho = tmp_path / "pesos_score.json"
        caminho.write_text("[1, 2, 3]", encoding="utf-8")
        pesos = rotas_leads._carregar_pesos_score(caminho)
        assert pesos == rotas_leads.PESOS_SCORE_PADRAO

    def test_arquivo_parcial_completa_com_o_padrao(self, tmp_path):
        caminho = tmp_path / "pesos_score.json"
        caminho.write_text('{"bonus_sem_instagram": 99}', encoding="utf-8")
        pesos = rotas_leads._carregar_pesos_score(caminho)
        assert pesos["bonus_sem_instagram"] == 99
        assert pesos["bonus_nicho_alvo"] == rotas_leads.PESOS_SCORE_PADRAO["bonus_nicho_alvo"]


class TestEquivalenciaScoreSqlEPython:
    """SQL_SCORE (usado pra ordenar/filtrar direto no banco) precisa devolver
    o mesmo número que calcular_score (usado pra exibir o score) pro mesmo
    lead - senão a ordenação da lista não bate com o valor mostrado."""

    CASOS = [
        dict(nota=5.0, num_avaliacoes=150, site_status="sem_site", site_problemas=None,
             instagram_url=None, nicho="Clínica Odontológica"),
        dict(nota=4.5, num_avaliacoes=20, site_status="site_ruim",
             site_problemas="feito em construtor pronto (Wix)", instagram_url="https://instagram.com/x",
             nicho="Salão de beleza"),
        dict(nota=4.0, num_avaliacoes=1500, site_status="site_ok", site_problemas=None,
             instagram_url=None, nicho="dentista"),
        dict(nota=None, num_avaliacoes=None, site_status=None, site_problemas=None,
             instagram_url=None, nicho=None),
        dict(nota=4.5, num_avaliacoes=60, site_status="sem_site",
             site_problemas="feito em construtor pronto (Canva)", instagram_url=None,
             nicho="clínica odontológica"),
    ]

    def test_score_sql_bate_com_calcular_score(self, cliente):
        conexao = sqlite3.connect(db.CAMINHO_BANCO)
        try:
            for i, caso in enumerate(self.CASOS):
                place_id = f"equiv-{i}"
                conexao.execute(
                    "INSERT INTO leads (place_id, nome, status, nota, num_avaliacoes, site_status, "
                    "site_problemas, instagram_url, nicho, visto_em, atualizado_em) "
                    "VALUES (?, ?, 'novo', ?, ?, ?, ?, ?, ?, '2026-01-01', '2026-01-01')",
                    (
                        place_id, f"Empresa {place_id}", caso["nota"], caso["num_avaliacoes"],
                        caso["site_status"], caso["site_problemas"], caso["instagram_url"], caso["nicho"],
                    ),
                )
            conexao.commit()

            for i, caso in enumerate(self.CASOS):
                place_id = f"equiv-{i}"
                (score_sql,) = conexao.execute(
                    f"SELECT {rotas_leads.SQL_SCORE} FROM leads WHERE place_id = ?", (place_id,)
                ).fetchone()
                score_python = calcular_score(
                    caso["nota"], caso["num_avaliacoes"], caso["site_status"],
                    site_problemas=caso["site_problemas"], instagram_url=caso["instagram_url"],
                    nicho=caso["nicho"],
                )
                assert round(score_sql) == score_python, caso
        finally:
            conexao.close()


class TestFiltroSituacaoDoSite:
    def test_filtra_por_site_ruim(self, cliente):
        inserir_lead("sem", site_status="sem_site")
        inserir_lead("ruim", site_status="site_ruim", site_problemas="sem HTTPS")

        leads = cliente.get("/api/leads?site_status=site_ruim").get_json()["leads"]
        assert [l["place_id"] for l in leads] == ["ruim"]

    def test_site_status_invalido_retorna_400(self, cliente):
        assert cliente.get("/api/leads?site_status=qualquer").status_code == 400


class TestFiltroFollowupVencido:
    def test_traz_so_vencidos_ordenados_pelo_mais_atrasado(self, cliente):
        ontem = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        anteontem = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        amanha = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        inserir_lead("ontem", status="contatado", proximo_followup=ontem)
        inserir_lead("anteontem", status="contatado", proximo_followup=anteontem)
        inserir_lead("futuro", status="contatado", proximo_followup=amanha)
        inserir_lead("sem-followup", status="novo")

        leads = cliente.get("/api/leads?followup=vencido").get_json()["leads"]
        assert [l["place_id"] for l in leads] == ["anteontem", "ontem"]

    def test_followup_invalido_retorna_400(self, cliente):
        assert cliente.get("/api/leads?followup=amanha").status_code == 400


class TestReanalisarSite:
    def test_reanalisa_lead_com_site(self, cliente, monkeypatch):
        import processar
        monkeypatch.setattr(
            processar, "avaliar_site_completo",
            lambda url: ("ruim", ["sem HTTPS"], {"tem": ["fotos do negócio"], "falta": ["botão de WhatsApp"]}),
        )
        inserir_lead("lead-1", site_status="site_ruim")
        conexao = sqlite3.connect(db.CAMINHO_BANCO)
        conexao.execute("UPDATE leads SET site_url = 'https://x.com.br' WHERE place_id = 'lead-1'")
        conexao.commit()
        conexao.close()

        resposta = cliente.post("/api/leads/lead-1/reanalisar-site")
        dados = resposta.get_json()
        assert resposta.status_code == 200
        assert dados["site_status"] == "site_ruim"
        assert dados["site_checklist"]["falta"] == ["botão de WhatsApp"]

        lead = cliente.get("/api/leads?status=novo").get_json()["leads"][0]
        assert lead["site_checklist"]["falta"] == ["botão de WhatsApp"]

    def test_site_que_melhorou_vira_site_ok(self, cliente, monkeypatch):
        import processar
        monkeypatch.setattr(
            processar, "avaliar_site_completo", lambda url: ("ok", [], {"tem": ["botão de WhatsApp"], "falta": []})
        )
        inserir_lead("lead-1", site_status="site_ruim", site_problemas="sem HTTPS")
        conexao = sqlite3.connect(db.CAMINHO_BANCO)
        conexao.execute("UPDATE leads SET site_url = 'https://x.com.br' WHERE place_id = 'lead-1'")
        conexao.commit()
        conexao.close()

        dados = cliente.post("/api/leads/lead-1/reanalisar-site").get_json()
        assert dados["site_status"] == "site_ok"
        assert dados["site_problemas"] is None

    def test_sem_site_tenta_achar_na_web(self, cliente, monkeypatch):
        import processar
        monkeypatch.setattr(processar, "buscar_site_da_empresa", lambda nome, endereco="": None)
        inserir_lead("lead-1", site_status="sem_site")

        dados = cliente.post("/api/leads/lead-1/reanalisar-site").get_json()
        assert dados["site_status"] == "sem_site"

    def test_lead_inexistente_retorna_404(self, cliente):
        assert cliente.post("/api/leads/nao-existe/reanalisar-site").status_code == 404


class TestHistoricoDeBuscas:
    def test_lista_ultimas_buscas(self, cliente):
        conexao = sqlite3.connect(db.CAMINHO_BANCO)
        for i, status in enumerate(["concluido", "erro", "interrompido"], start=1):
            conexao.execute(
                "INSERT INTO jobs (tipo, status, mensagem, iniciado_em) VALUES ('busca_maps', ?, ?, ?)",
                (status, f"busca {i}", f"2026-07-1{i}T10:00:00"),
            )
        conexao.execute(
            "INSERT INTO jobs (tipo, status, iniciado_em) VALUES ('analise_instagram', 'concluido', '2026-07-14T10:00:00')"
        )
        conexao.commit()
        conexao.close()

        buscas = cliente.get("/api/buscar/historico").get_json()["buscas"]
        assert len(buscas) == 3  # só busca_maps, análise do IG fica de fora
        assert buscas[0]["mensagem"] == "busca 3"  # mais recente primeiro


class TestTarefasHoje:
    def test_estrutura_vazia(self, cliente):
        dados = cliente.get("/api/tarefas-hoje").get_json()
        assert dados == {"followups": [], "novos_quentes": []}

    def test_followups_vencidos_dos_dois_canais_ordenados(self, cliente):
        ontem = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        anteontem = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        amanha = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        inserir_lead("maps-vencido", status="contatado", proximo_followup=ontem,
                     mensagem_gerada="Olá!")
        inserir_lead("maps-futuro", status="contatado", proximo_followup=amanha)
        inserir_lead_instagram("ig_vencido", proximo_followup=anteontem, sugestao_dm="Oi!")

        followups = cliente.get("/api/tarefas-hoje").get_json()["followups"]
        assert [(f["canal"], f["titulo"]) for f in followups] == [
            ("instagram", "@ig_vencido"),  # mais atrasado primeiro
            ("maps", "Empresa maps-vencido"),
        ]
        assert followups[0]["mensagem"] == "Oi!"
        assert followups[1]["whatsapp_link"] == "https://wa.me/5511999999999"

    def test_novos_quentes_ordenados_por_score_max_5(self, cliente):
        for i in range(6):
            inserir_lead(f"novo-{i}", nota=4.0 + i * 0.1, num_avaliacoes=10 * i)
        inserir_lead("contatado", nota=5.0, num_avaliacoes=500, status="contatado")

        quentes = cliente.get("/api/tarefas-hoje").get_json()["novos_quentes"]
        assert len(quentes) == 5  # limite, e só status 'novo'
        assert quentes[0]["id"] == "novo-5"  # maior score primeiro
        assert all(q["score"] >= quentes[-1]["score"] for q in quentes)
        assert "contatado" not in [q["id"] for q in quentes]
