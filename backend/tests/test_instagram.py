"""Testes de integração das rotas do Instagram - mesmo padrão do test_app.py:
banco SQLite temporário via monkeypatch em db.CAMINHO_BANCO, nunca o leads.db real."""

import sqlite3

import pytest

import app as app_module
import constantes
import db
import jobs
import processar


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


def inserir_post(post_url="https://www.instagram.com/p/ABC123/", **overrides):
    campos = {
        "post_url": post_url,
        "criado_em": "2026-01-01T00:00:00",
        "etapa": "concluido",
        "arquivado_em": None,
        "nicho_alvo": None,
        "arquivo_comentarios": None,
    }
    campos.update(overrides)

    conexao = sqlite3.connect(db.CAMINHO_BANCO)
    cursor = conexao.execute(
        "INSERT INTO instagram_posts (post_url, criado_em, etapa, arquivado_em, nicho_alvo, arquivo_comentarios) "
        "VALUES (:post_url, :criado_em, :etapa, :arquivado_em, :nicho_alvo, :arquivo_comentarios)",
        campos,
    )
    conexao.commit()
    post_id = cursor.lastrowid
    conexao.close()
    return post_id


def inserir_lead_instagram(username, post_id, **overrides):
    campos = {
        "post_id": post_id,
        "username": username,
        "full_name": "Nome Teste",
        "is_private": 0,
        "biography": "Bio de teste",
        "seguidores": 100,
        "is_business_account": 1,
        "comentarios": '["comentário 1"]',
        "prioridade": "alta",
        "status": "novo",
        "nicho": "esteticista",
        "atualizado_em": "2026-01-01T00:00:00",
    }
    campos.update(overrides)

    conexao = sqlite3.connect(db.CAMINHO_BANCO)
    cursor = conexao.execute(
        """
        INSERT INTO instagram_leads (post_id, username, full_name, is_private, biography,
                                     seguidores, is_business_account, comentarios, prioridade,
                                     status, nicho, atualizado_em)
        VALUES (:post_id, :username, :full_name, :is_private, :biography,
                :seguidores, :is_business_account, :comentarios, :prioridade,
                :status, :nicho, :atualizado_em)
        """,
        campos,
    )
    conexao.commit()
    lead_id = cursor.lastrowid
    conexao.close()
    return lead_id


class TestAnalisarPost:
    def test_url_invalida_retorna_400(self, cliente):
        resposta = cliente.post("/api/instagram/analisar", json={"post_url": "https://exemplo.com/foo"})
        assert resposta.status_code == 400

    def test_url_vazia_retorna_400(self, cliente):
        resposta = cliente.post("/api/instagram/analisar", json={"post_url": ""})
        assert resposta.status_code == 400

    def test_analise_ja_rodando_retorna_409(self, cliente):
        jobs.estado_instagram["rodando"] = True
        try:
            resposta = cliente.post(
                "/api/instagram/analisar",
                json={"post_url": "https://www.instagram.com/p/ABC123/"},
            )
            assert resposta.status_code == 409
        finally:
            jobs.estado_instagram["rodando"] = False

    def test_dispara_analise_e_cria_post(self, cliente, monkeypatch):
        # não sobe a thread real (que exigiria sessão do instagrapi) - só valida
        # o registro do post e a resposta da rota
        monkeypatch.setattr(jobs, "iniciar_thread_analise_instagram", lambda *args: None)
        try:
            resposta = cliente.post(
                "/api/instagram/analisar",
                json={"post_url": "https://www.instagram.com/p/ABC123/", "nicho_alvo": "estética"},
            )
            assert resposta.status_code == 200
            post_id = resposta.get_json()["post_id"]

            conexao = sqlite3.connect(db.CAMINHO_BANCO)
            linha = conexao.execute(
                "SELECT post_url, etapa, nicho_alvo FROM instagram_posts WHERE id = ?", (post_id,)
            ).fetchone()
            conexao.close()
            assert linha == ("https://www.instagram.com/p/ABC123/", "pendente", "estética")
        finally:
            jobs.liberar_analise_instagram()


class TestListarPosts:
    def test_lista_vazia(self, cliente):
        resposta = cliente.get("/api/instagram/posts")
        assert resposta.status_code == 200
        assert resposta.get_json()["posts"] == []

    def test_lista_posts_com_contagem_de_leads(self, cliente):
        post_id = inserir_post()
        inserir_lead_instagram("user1", post_id, prioridade="alta")
        inserir_lead_instagram("user2", post_id, prioridade="media")
        inserir_lead_instagram("user3", post_id, prioridade=None, status="ignorado")

        resposta = cliente.get("/api/instagram/posts")
        posts = resposta.get_json()["posts"]
        assert len(posts) == 1
        contagem = posts[0]["contagem_leads"]
        assert contagem["alta"] == 1
        assert contagem["media"] == 1
        assert contagem["ignorado"] == 1
        assert contagem["total"] == 3

    def test_arquivados_ficam_fora_da_lista_principal(self, cliente):
        inserir_post(post_url="https://www.instagram.com/p/ATIVO/")
        inserir_post(post_url="https://www.instagram.com/p/ARQUIVADO/", arquivado_em="2026-01-02T00:00:00")

        ativos = cliente.get("/api/instagram/posts").get_json()["posts"]
        arquivados = cliente.get("/api/instagram/posts?arquivados=true").get_json()["posts"]
        assert [p["post_url"] for p in ativos] == ["https://www.instagram.com/p/ATIVO/"]
        assert [p["post_url"] for p in arquivados] == ["https://www.instagram.com/p/ARQUIVADO/"]


class TestListarLeads:
    def test_esconde_ignorados_por_padrao(self, cliente):
        post_id = inserir_post()
        inserir_lead_instagram("ativo", post_id, status="novo")
        inserir_lead_instagram("escondido", post_id, status="ignorado")

        leads = cliente.get(f"/api/instagram/posts/{post_id}/leads").get_json()["leads"]
        assert [l["username"] for l in leads] == ["ativo"]

    def test_filtro_por_status_explicito(self, cliente):
        post_id = inserir_post()
        inserir_lead_instagram("ativo", post_id, status="novo")
        inserir_lead_instagram("escondido", post_id, status="ignorado")

        leads = cliente.get(f"/api/instagram/posts/{post_id}/leads?status=ignorado").get_json()["leads"]
        assert [l["username"] for l in leads] == ["escondido"]

    def test_busca_textual_em_username_e_bio(self, cliente):
        post_id = inserir_post()
        inserir_lead_instagram("dra_ana", post_id, biography="Advogada em Vitória")
        inserir_lead_instagram("outro", post_id, biography="Perfil qualquer")

        leads = cliente.get(f"/api/instagram/posts/{post_id}/leads?busca=Advogada").get_json()["leads"]
        assert [l["username"] for l in leads] == ["dra_ana"]

    def test_comentarios_vem_como_lista(self, cliente):
        post_id = inserir_post()
        inserir_lead_instagram("user1", post_id, comentarios='["oi", "quero saber mais"]')

        leads = cliente.get(f"/api/instagram/posts/{post_id}/leads").get_json()["leads"]
        assert leads[0]["comentarios"] == ["oi", "quero saber mais"]

    def test_comentario_com_json_invalido_nao_derruba_a_lista(self, cliente):
        """Uma linha com comentarios corrompido não pode dar 500 e esconder os
        outros leads do post - vira lista vazia só naquele lead."""
        post_id = inserir_post()
        inserir_lead_instagram("bom", post_id, comentarios='["ok"]')
        inserir_lead_instagram("corrompido", post_id, comentarios="isto não é json{{")

        resposta = cliente.get(f"/api/instagram/posts/{post_id}/leads")
        assert resposta.status_code == 200
        leads = {l["username"]: l["comentarios"] for l in resposta.get_json()["leads"]}
        assert leads == {"bom": ["ok"], "corrompido": []}

    def test_exportar_csv_tolera_json_invalido(self, cliente):
        post_id = inserir_post()
        inserir_lead_instagram("corrompido", post_id, comentarios="{quebrado")

        resposta = cliente.get(f"/api/instagram/posts/{post_id}/exportar")
        assert resposta.status_code == 200


class TestStatusLead:
    def test_atualiza_status_e_grava_historico(self, cliente):
        post_id = inserir_post()
        lead_id = inserir_lead_instagram("user1", post_id, status="novo")

        resposta = cliente.post(f"/api/instagram/leads/{lead_id}/status", json={"status": "contatado"})
        assert resposta.status_code == 200

        historico = cliente.get(f"/api/instagram/leads/{lead_id}/historico").get_json()
        assert len(historico) == 1
        assert historico[0]["status_anterior"] == "novo"
        assert historico[0]["status_novo"] == "contatado"

    def test_status_invalido_retorna_400(self, cliente):
        post_id = inserir_post()
        lead_id = inserir_lead_instagram("user1", post_id)
        resposta = cliente.post(f"/api/instagram/leads/{lead_id}/status", json={"status": "invalido"})
        assert resposta.status_code == 400

    def test_lead_inexistente_retorna_404(self, cliente):
        resposta = cliente.post("/api/instagram/leads/9999/status", json={"status": "contatado"})
        assert resposta.status_code == 404

    def test_status_que_encerra_followup_limpa_proximo(self, cliente):
        post_id = inserir_post()
        lead_id = inserir_lead_instagram("user1", post_id, status="contatado")
        cliente.post(f"/api/instagram/leads/{lead_id}/followup", json={"proximo_followup": "2026-08-01"})

        cliente.post(f"/api/instagram/leads/{lead_id}/status", json={"status": "fechou"})

        conexao = sqlite3.connect(db.CAMINHO_BANCO)
        proximo = conexao.execute(
            "SELECT proximo_followup FROM instagram_leads WHERE id = ?", (lead_id,)
        ).fetchone()[0]
        conexao.close()
        assert proximo is None

    def test_bulk_status(self, cliente):
        post_id = inserir_post()
        id1 = inserir_lead_instagram("user1", post_id)
        id2 = inserir_lead_instagram("user2", post_id)

        resposta = cliente.post(
            "/api/instagram/leads/bulk-status",
            json={"lead_ids": [id1, id2, 9999], "status": "contatado"},
        )
        assert resposta.status_code == 200
        assert resposta.get_json()["atualizados"] == 2


class TestExclusao:
    def test_so_exclui_lead_ignorado(self, cliente):
        post_id = inserir_post()
        lead_id = inserir_lead_instagram("user1", post_id, status="novo")

        assert cliente.delete(f"/api/instagram/leads/{lead_id}").status_code == 400

        cliente.post(f"/api/instagram/leads/{lead_id}/ignorar")
        assert cliente.delete(f"/api/instagram/leads/{lead_id}").status_code == 200

    def test_bulk_exclui_so_os_ignorados(self, cliente):
        post_id = inserir_post()
        id1 = inserir_lead_instagram("user1", post_id, status="ignorado")
        id2 = inserir_lead_instagram("user2", post_id, status="novo")

        resposta = cliente.post("/api/instagram/leads/bulk-excluir", json={"lead_ids": [id1, id2]})
        assert resposta.status_code == 200
        assert resposta.get_json()["excluidos"] == 1

    def test_excluir_post_exige_arquivamento(self, cliente):
        post_id = inserir_post()
        assert cliente.delete(f"/api/instagram/posts/{post_id}").status_code == 400

        cliente.post(f"/api/instagram/posts/{post_id}/arquivar")
        assert cliente.delete(f"/api/instagram/posts/{post_id}").status_code == 200

    def test_excluir_post_apaga_leads_e_historico(self, cliente):
        post_id = inserir_post()
        lead_id = inserir_lead_instagram("user1", post_id)
        cliente.post(f"/api/instagram/leads/{lead_id}/status", json={"status": "contatado"})
        cliente.post(f"/api/instagram/posts/{post_id}/arquivar")

        assert cliente.delete(f"/api/instagram/posts/{post_id}").status_code == 200

        conexao = sqlite3.connect(db.CAMINHO_BANCO)
        leads = conexao.execute("SELECT COUNT(*) FROM instagram_leads").fetchone()[0]
        historico = conexao.execute("SELECT COUNT(*) FROM historico_status_instagram").fetchone()[0]
        conexao.close()
        assert leads == 0
        assert historico == 0


class TestObservacoesTagsEFollowup:
    def test_observacoes_muito_longas_retorna_400(self, cliente):
        post_id = inserir_post()
        lead_id = inserir_lead_instagram("user1", post_id)
        texto = "a" * (constantes.MAX_CARACTERES_OBSERVACOES_INSTAGRAM + 1)
        resposta = cliente.post(f"/api/instagram/leads/{lead_id}/observacoes", json={"observacoes": texto})
        assert resposta.status_code == 400

    def test_tags_muito_longas_retorna_400(self, cliente):
        post_id = inserir_post()
        lead_id = inserir_lead_instagram("user1", post_id)
        tags = "a" * (constantes.MAX_CARACTERES_TAGS_INSTAGRAM + 1)
        resposta = cliente.post(f"/api/instagram/leads/{lead_id}/tags", json={"tags": tags})
        assert resposta.status_code == 400

    def test_marcar_followup_enviado_sugere_cadencia(self, cliente):
        post_id = inserir_post()
        lead_id = inserir_lead_instagram("user1", post_id)

        resposta = cliente.post(f"/api/instagram/leads/{lead_id}/marcar-followup-enviado")
        dados = resposta.get_json()
        assert dados["follow_ups_enviados"] == 1
        assert dados["proximo_followup_sugerido"]  # 1º follow-up: +3 dias

    def test_desfazer_followup_restaura_valores(self, cliente):
        post_id = inserir_post()
        lead_id = inserir_lead_instagram("user1", post_id)
        cliente.post(f"/api/instagram/leads/{lead_id}/marcar-followup-enviado")

        resposta = cliente.post(
            f"/api/instagram/leads/{lead_id}/desfazer-followup-enviado",
            json={
                "follow_ups_enviados_anterior": 0,
                "ultimo_followup_em_anterior": None,
                "proximo_followup_anterior": None,
            },
        )
        assert resposta.status_code == 200

        conexao = sqlite3.connect(db.CAMINHO_BANCO)
        linha = conexao.execute(
            "SELECT follow_ups_enviados, proximo_followup FROM instagram_leads WHERE id = ?",
            (lead_id,),
        ).fetchone()
        conexao.close()
        assert linha == (0, None)


class TestAnaliseManual:
    def test_grava_analise_valida(self, cliente):
        post_id = inserir_post()
        lead_id = inserir_lead_instagram("user1", post_id, prioridade=None)

        resposta = cliente.post(
            f"/api/instagram/leads/{lead_id}/analise",
            json={"prioridade": "alta", "justificativa": "bom lead", "sugestao_dm": "oi", "nicho": "dentista"},
        )
        assert resposta.status_code == 200

    def test_prioridade_invalida_retorna_400(self, cliente):
        post_id = inserir_post()
        lead_id = inserir_lead_instagram("user1", post_id)
        resposta = cliente.post(
            f"/api/instagram/leads/{lead_id}/analise", json={"prioridade": "urgentissima"}
        )
        assert resposta.status_code == 400


class TestRetomarAnalise:
    def _post_com_erro(self, tmp_path, arquivo_existe=True):
        arquivo = tmp_path / "post_123.json"
        if arquivo_existe:
            arquivo.write_text('{"comentarios": []}', encoding="utf-8")
        return inserir_post(etapa="erro", arquivo_comentarios=str(arquivo))

    def test_retoma_analise_com_erro(self, cliente, tmp_path, monkeypatch):
        disparos = []
        monkeypatch.setattr(
            jobs, "iniciar_thread_analise_instagram", lambda *args: disparos.append(args)
        )
        post_id = self._post_com_erro(tmp_path)
        try:
            resposta = cliente.post(f"/api/instagram/posts/{post_id}/retomar")
            assert resposta.status_code == 200
            assert len(disparos) == 1
            assert disparos[0][0] == post_id
            assert disparos[0][3].endswith("post_123.json")  # reusa os comentários raspados

            conexao = sqlite3.connect(db.CAMINHO_BANCO)
            etapa, erro = conexao.execute(
                "SELECT etapa, erro_mensagem FROM instagram_posts WHERE id = ?", (post_id,)
            ).fetchone()
            conexao.close()
            assert etapa == "pendente"
            assert erro is None
        finally:
            jobs.liberar_analise_instagram()

    def test_post_concluido_nao_retoma(self, cliente, tmp_path):
        arquivo = tmp_path / "post_123.json"
        arquivo.write_text("{}", encoding="utf-8")
        post_id = inserir_post(etapa="concluido", arquivo_comentarios=str(arquivo))
        assert cliente.post(f"/api/instagram/posts/{post_id}/retomar").status_code == 400

    def test_sem_arquivo_de_comentarios_nao_retoma(self, cliente, tmp_path):
        post_id = self._post_com_erro(tmp_path, arquivo_existe=False)
        resposta = cliente.post(f"/api/instagram/posts/{post_id}/retomar")
        assert resposta.status_code == 400

    def test_post_inexistente_retorna_404(self, cliente):
        assert cliente.post("/api/instagram/posts/9999/retomar").status_code == 404

    def test_analise_rodando_retorna_409(self, cliente, tmp_path):
        post_id = self._post_com_erro(tmp_path)
        jobs.estado_instagram["rodando"] = True
        try:
            assert cliente.post(f"/api/instagram/posts/{post_id}/retomar").status_code == 409
        finally:
            jobs.estado_instagram["rodando"] = False

    def test_listar_posts_expoe_pode_retomar(self, cliente, tmp_path):
        retomavel = self._post_com_erro(tmp_path)
        normal = inserir_post(post_url="https://www.instagram.com/p/OK/")

        posts = {p["id"]: p for p in cliente.get("/api/instagram/posts").get_json()["posts"]}
        assert posts[retomavel]["pode_retomar"] is True
        assert posts[normal]["pode_retomar"] is False


class TestUsernameUnico:
    def test_nao_permite_username_duplicado(self, cliente):
        """O índice único criado na migração garante 1 lead por username,
        mesmo entre posts diferentes."""
        post_a = inserir_post(post_url="https://www.instagram.com/p/A/")
        post_b = inserir_post(post_url="https://www.instagram.com/p/B/")
        inserir_lead_instagram("mesma_pessoa", post_a)

        with pytest.raises(sqlite3.IntegrityError):
            inserir_lead_instagram("mesma_pessoa", post_b)
