"""
Testes das funções puras de processar.py (sem depender de rede, scraper ou banco real).
Rodar com: py -m pytest
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import processar
from processar import (
    dominio_e_proprio,
    extrair_nicho_e_cidade,
    linha_qualifica,
    mapear_queries_por_input_id,
    telefone_para_whatsapp,
)


class TestTelefoneParaWhatsapp:
    def test_celular_com_nove_digitos_e_ddd_curitiba(self):
        assert telefone_para_whatsapp("(41) 98999-0011") == "https://wa.me/5541989990011"

    def test_ja_vem_com_ddi_55(self):
        assert telefone_para_whatsapp("5541989990011") == "https://wa.me/5541989990011"

    def test_celular_sem_o_nove_em_ddd_que_exige(self):
        # DDD 11 (São Paulo) está na lista DDDS_COM_NOVE; número de 8 dígitos deve ganhar o "9"
        assert telefone_para_whatsapp("(11) 8999-0011") == "https://wa.me/5511989990011"

    def test_com_zero_de_discagem_interurbana(self):
        assert telefone_para_whatsapp("041989990011") == "https://wa.me/5541989990011"

    def test_ddd_que_nao_exige_o_nove_fica_como_esta(self):
        # DDD 47 (Santa Catarina) não está na lista DDDS_COM_NOVE
        resultado = telefone_para_whatsapp("(47) 3222-0011")
        assert resultado == "https://wa.me/554732220011"

    def test_vazio_retorna_none(self):
        assert telefone_para_whatsapp("") is None
        assert telefone_para_whatsapp(None) is None

    def test_so_letras_retorna_none(self):
        assert telefone_para_whatsapp("não tem telefone") is None

    def test_numero_muito_curto_retorna_none(self):
        assert telefone_para_whatsapp("12345") is None

    def test_numero_muito_longo_retorna_none(self):
        assert telefone_para_whatsapp("123456789012345") is None


class TestLinhaQualifica:
    def test_nota_com_virgula_decimal(self):
        linha = {"website": "", "review_rating": "4,5"}
        assert linha_qualifica(linha) is True

    def test_nota_com_ponto_decimal(self):
        linha = {"website": "", "review_rating": "4.5"}
        assert linha_qualifica(linha) is True

    def test_nota_abaixo_do_minimo(self):
        linha = {"website": "", "review_rating": "3.9"}
        assert linha_qualifica(linha) is False

    def test_nota_exatamente_no_minimo(self):
        linha = {"website": "", "review_rating": "4.0"}
        assert linha_qualifica(linha) is True

    def test_com_site_preenchido_nao_desqualifica_mais(self):
        # desde a detecção de "site ruim", ter site não elimina o lead no filtro
        # rápido - a qualidade do site é avaliada depois, com rede
        linha = {"website": "https://empresa.com.br", "review_rating": "5.0"}
        assert linha_qualifica(linha) is True

    def test_nota_ausente_desqualifica(self):
        linha = {"website": "", "review_rating": ""}
        assert linha_qualifica(linha) is False

    def test_nota_invalida_desqualifica(self):
        linha = {"website": "", "review_rating": "não é nota"}
        assert linha_qualifica(linha) is False


class RespostaFake:
    def __init__(self, status_code=200, url="https://site.com.br/", text="", segundos_resposta=0.5):
        from datetime import timedelta
        self.status_code = status_code
        self.url = url
        self.text = text
        self.elapsed = timedelta(seconds=segundos_resposta)


HTML_SITE_BOM = "<html><head><meta name='viewport' content='width=device-width'></head><body>" + "conteúdo " * 200 + "</body></html>"


class TestAvaliarSite:
    def test_site_bom_e_ok(self, monkeypatch):
        import requests
        monkeypatch.setattr(requests, "get", lambda *a, **kw: RespostaFake(text=HTML_SITE_BOM))

        assert processar.avaliar_site("https://site.com.br") == ("ok", [])

    def test_site_sem_viewport_e_ruim(self, monkeypatch):
        import requests
        html = "<html><body>" + "conteúdo " * 200 + "</body></html>"
        monkeypatch.setattr(requests, "get", lambda *a, **kw: RespostaFake(text=html))

        situacao, problemas = processar.avaliar_site("https://site.com.br")
        assert situacao == "ruim"
        assert any("celular" in p for p in problemas)

    def test_site_fora_do_ar_e_ruim(self, monkeypatch):
        import requests

        def explode(*a, **kw):
            raise requests.exceptions.ConnectionError("conexão recusada")

        monkeypatch.setattr(requests, "get", explode)
        monkeypatch.setattr(processar.time, "sleep", lambda s: None)

        situacao, problemas = processar.avaliar_site("https://naoexiste.com.br")
        assert situacao == "ruim"
        assert any("fora do ar" in p for p in problemas)

    def test_site_com_erro_http_e_ruim(self, monkeypatch):
        import requests
        monkeypatch.setattr(
            requests, "get", lambda *a, **kw: RespostaFake(status_code=500, text=HTML_SITE_BOM)
        )

        situacao, problemas = processar.avaliar_site("https://site.com.br")
        assert situacao == "ruim"
        assert any("HTTP 500" in p for p in problemas)

    def test_site_sem_https_e_ruim(self, monkeypatch):
        import requests
        monkeypatch.setattr(
            requests, "get",
            lambda *a, **kw: RespostaFake(url="http://site.com.br/", text=HTML_SITE_BOM),
        )

        situacao, problemas = processar.avaliar_site("http://site.com.br")
        assert situacao == "ruim"
        assert any("HTTPS" in p for p in problemas)

    def test_ssl_invalido_e_ruim_mas_continua_avaliando(self, monkeypatch):
        import requests
        chamadas = []

        def get_fake(*a, **kw):
            chamadas.append(kw.get("verify", True))
            if kw.get("verify", True):
                raise requests.exceptions.SSLError("certificado vencido")
            return RespostaFake(text=HTML_SITE_BOM)

        monkeypatch.setattr(requests, "get", get_fake)

        situacao, problemas = processar.avaliar_site("https://site.com.br")
        assert situacao == "ruim"
        assert any("SSL" in p for p in problemas)
        assert chamadas == [True, False]  # tentou com verificação, refez sem

    def test_url_sem_esquema_que_so_responde_em_http_vira_sem_https(self, monkeypatch):
        """Servidor sem porta 443: o diagnóstico correto é 'sem HTTPS', não 'fora do ar'."""
        import requests
        urls_tentadas = []

        def get_fake(url_alvo, *a, **kw):
            urls_tentadas.append(url_alvo)
            if url_alvo.startswith("https://"):
                raise requests.exceptions.ConnectionError("porta 443 fechada")
            return RespostaFake(url="http://sitesohttp.com.br/", text=HTML_SITE_BOM)

        monkeypatch.setattr(requests, "get", get_fake)
        monkeypatch.setattr(processar.time, "sleep", lambda s: None)

        situacao, problemas = processar.avaliar_site("sitesohttp.com.br")
        assert situacao == "ruim"
        assert any("sem HTTPS" in p for p in problemas)
        assert not any("fora do ar" in p for p in problemas)
        # https é tentado 2x (retentativa transitória) antes do fallback pra http
        assert urls_tentadas == [
            "https://sitesohttp.com.br", "https://sitesohttp.com.br", "http://sitesohttp.com.br",
        ]

    def test_url_sem_esquema_com_http_tambem_morto_e_fora_do_ar(self, monkeypatch):
        import requests

        def explode(*a, **kw):
            raise requests.exceptions.ConnectionError("nada responde")

        monkeypatch.setattr(requests, "get", explode)
        monkeypatch.setattr(processar.time, "sleep", lambda s: None)

        situacao, problemas = processar.avaliar_site("dominioquebrado.com.br")
        assert situacao == "ruim"
        assert any("fora do ar" in p for p in problemas)

    def test_conteudo_misto_em_pagina_https(self, monkeypatch):
        import requests
        html = HTML_SITE_BOM.replace(
            "</body>", '<img src="http://cdn-antigo.com.br/logo.png"></body>'
        )
        monkeypatch.setattr(
            requests, "get", lambda *a, **kw: RespostaFake(url="https://site.com.br/", text=html)
        )

        situacao, problemas = processar.avaliar_site("https://site.com.br")
        assert situacao == "ruim"
        assert any("conteúdo misto" in p for p in problemas)

    def test_link_http_de_navegacao_nao_e_conteudo_misto(self, monkeypatch):
        """<a href=http://...> é só um link externo - não carrega recurso, não é misto."""
        import requests
        html = HTML_SITE_BOM.replace(
            "</body>", '<a href="http://parceiro.com.br">parceiro</a></body>'
        )
        monkeypatch.setattr(
            requests, "get", lambda *a, **kw: RespostaFake(url="https://site.com.br/", text=html)
        )

        assert processar.avaliar_site("https://site.com.br") == ("ok", [])

    def test_ssl_invalido_com_fallback_tambem_morto_preserva_o_motivo(self, monkeypatch):
        import requests

        def get_fake(*a, **kw):
            if kw.get("verify", True):
                raise requests.exceptions.SSLError("certificado vencido")
            raise requests.exceptions.ConnectionError("caiu de vez")

        monkeypatch.setattr(requests, "get", get_fake)

        situacao, problemas = processar.avaliar_site("https://site.com.br")
        assert situacao == "ruim"
        assert any("SSL" in p for p in problemas)
        assert any("fora do ar" in p for p in problemas)

    def test_site_lento_mas_funcional_e_ruim(self, monkeypatch):
        """Site que 'funciona mas demora' agora é lead - antes passava como ok."""
        import requests
        monkeypatch.setattr(
            requests, "get",
            lambda *a, **kw: RespostaFake(text=HTML_SITE_BOM, segundos_resposta=8),
        )

        situacao, problemas = processar.avaliar_site("https://site-lento.com.br")
        assert situacao == "ruim"
        assert any("lento" in p and "8s" in p for p in problemas)

    def test_site_rapido_nao_e_marcado_como_lento(self, monkeypatch):
        import requests
        monkeypatch.setattr(
            requests, "get",
            lambda *a, **kw: RespostaFake(text=HTML_SITE_BOM, segundos_resposta=1.2),
        )

        assert processar.avaliar_site("https://site-rapido.com.br") == ("ok", [])

    def test_pagina_quase_vazia_e_ruim(self, monkeypatch):
        import requests
        monkeypatch.setattr(
            requests, "get",
            lambda *a, **kw: RespostaFake(text="<html><head><meta name='viewport'></head><body>oi</body></html>"),
        )

        situacao, problemas = processar.avaliar_site("https://site.com.br")
        assert situacao == "ruim"
        assert any("vazia" in p for p in problemas)


class TestChecagemDeOnlineInteligente:
    def test_falha_transitoria_ganha_nova_tentativa(self, monkeypatch):
        """1ª conexão falha, 2ª funciona: não é falso 'fora do ar'."""
        import requests
        tentativas = []

        def get_instavel(url_alvo, *a, **kw):
            tentativas.append(url_alvo)
            if len(tentativas) == 1:
                raise requests.exceptions.ConnectionError("engasgo de rede")
            return RespostaFake(text=HTML_SITE_BOM)

        monkeypatch.setattr(requests, "get", get_instavel)
        monkeypatch.setattr(processar.time, "sleep", lambda s: None)

        situacao, _problemas = processar.avaliar_site("https://site.com.br")
        assert situacao == "ok"
        assert len(tentativas) == 2

    def test_dns_morto_vira_dominio_expirado_sem_retentativa(self, monkeypatch):
        import requests
        tentativas = []

        def get_dns_morto(url_alvo, *a, **kw):
            tentativas.append(url_alvo)
            raise requests.exceptions.ConnectionError(
                "[Errno 11001] getaddrinfo failed"
            )

        monkeypatch.setattr(requests, "get", get_dns_morto)

        situacao, problemas = processar.avaliar_site("https://dominio-abandonado.com.br")
        assert situacao == "ruim"
        assert any("domínio não encontrado" in p for p in problemas)
        assert len(tentativas) == 1  # DNS morto é definitivo, não tenta de novo


HTML_COMPLETO = """<html><head>
<title>Clínica Sorriso - Dentista em Vitória ES</title>
<meta name="description" content="Tratamentos odontológicos completos com tecnologia e carinho desde 2010.">
<link rel="icon" href="/favicon.ico">
<meta name="viewport" content="width=device-width">
</head><body>
<a href="https://wa.me/5527999999999">WhatsApp</a>
<a href="tel:+5527999999999">Ligar</a>
<a href="mailto:contato@sorriso.com.br">E-mail</a>
<a href="https://instagram.com/clinicasorriso">Instagram</a>
<p>Av. Central, 100 - Vitória - ES, 29000-000</p>
<img src="/f1.jpg"><img src="/f2.jpg"><img src="/f3.jpg"><img src="/f4.jpg">
""" + "<p>conteúdo</p>" * 100 + "</body></html>"


class TestChecklistDoSite:
    def test_site_completo_tem_tudo(self):
        checklist, _ano = processar.montar_checklist_site(HTML_COMPLETO, "https://sorriso.com.br/")
        assert checklist["falta"] == []
        assert "botão de WhatsApp" in checklist["tem"]
        assert "telefone clicável" in checklist["tem"]
        assert "fotos do negócio" in checklist["tem"]
        assert "descrição para aparecer no Google" in checklist["tem"]

    def test_site_pelado_falta_quase_tudo(self):
        html = "<html><head><title>Home</title></head><body><p>oi</p></body></html>"
        checklist, _ano = processar.montar_checklist_site(html, "https://x.com.br/")
        assert "botão de WhatsApp" in checklist["falta"]
        assert "telefone clicável" in checklist["falta"]
        assert "fotos do negócio" in checklist["falta"]
        assert "título descritivo na aba" in checklist["falta"]  # "Home" não conta
        assert "descrição para aparecer no Google" in checklist["falta"]

    def test_copyright_antigo_vira_problema(self, monkeypatch):
        import requests
        html = HTML_SITE_BOM.replace("</body>", "<footer>© 2019 Empresa</footer></body>")
        monkeypatch.setattr(requests, "get", lambda *a, **kw: RespostaFake(text=html))

        situacao, problemas, checklist = processar.avaliar_site_completo("https://antigo.com.br")
        assert situacao == "ruim"
        assert any("desde 2019" in p for p in problemas)
        assert checklist is not None

    def test_avaliar_completo_retorna_checklist_e_fora_do_ar_retorna_none(self, monkeypatch):
        import requests

        def explode(*a, **kw):
            raise requests.exceptions.ConnectionError("getaddrinfo failed")

        monkeypatch.setattr(requests, "get", explode)
        _situacao, _problemas, checklist = processar.avaliar_site_completo("https://x.com.br")
        assert checklist is None


class TestDetectorDeConstrutor:
    def test_detecta_wix_pela_url(self, monkeypatch):
        import requests
        monkeypatch.setattr(
            requests, "get",
            lambda *a, **kw: RespostaFake(url="https://clinica.wixsite.com/inicio", text=HTML_SITE_BOM),
        )

        situacao, problemas = processar.avaliar_site("https://clinica.wixsite.com/inicio")
        assert situacao == "ruim"
        assert any("construtor pronto (Wix)" in p for p in problemas)

    def test_detecta_wix_pelo_html(self, monkeypatch):
        import requests
        html = HTML_SITE_BOM.replace("</body>", '<img src="https://static.wixstatic.com/x.png"></body>')
        monkeypatch.setattr(requests, "get", lambda *a, **kw: RespostaFake(text=html))

        situacao, problemas = processar.avaliar_site("https://dominio-proprio.com.br")
        assert situacao == "ruim"
        assert any("Wix" in p for p in problemas)

    def test_detecta_google_sites_e_canva(self):
        assert processar.detectar_construtor_generico("https://sites.google.com/view/x", "") == "Google Sites"
        assert processar.detectar_construtor_generico("https://algo.my.canva.site/", "") == "Canva"

    def test_site_proprio_nao_dispara(self, monkeypatch):
        import requests
        monkeypatch.setattr(requests, "get", lambda *a, **kw: RespostaFake(text=HTML_SITE_BOM))

        assert processar.avaliar_site("https://site-proprio.com.br") == ("ok", [])


class TestCapturarConteudoSite:
    HTML = (
        "<html><head><title>Clínica Sorriso - Dentista em Vitória</title>"
        '<meta name="description" content="Tratamentos odontológicos desde 2010">'
        "</head><body><h1>Bem-vindo à Clínica Sorriso</h1>"
        "<script>var x = 'nao deve aparecer';</script>"
        "<p>Cuidamos do seu sorriso com carinho e tecnologia.</p></body></html>"
    )

    def test_extrai_titulo_descricao_e_texto(self, monkeypatch):
        import requests
        monkeypatch.setattr(requests, "get", lambda *a, **kw: RespostaFake(text=self.HTML))

        conteudo = processar.capturar_conteudo_site("https://clinica.com.br")
        assert "Clínica Sorriso - Dentista em Vitória" in conteudo
        assert "Tratamentos odontológicos desde 2010" in conteudo
        assert "Bem-vindo à Clínica Sorriso" in conteudo
        assert "Cuidamos do seu sorriso" in conteudo
        assert "nao deve aparecer" not in conteudo

    def test_falha_de_rede_retorna_none(self, monkeypatch):
        import requests

        def explode(*a, **kw):
            raise requests.exceptions.ConnectionError("caiu")

        monkeypatch.setattr(requests, "get", explode)
        assert processar.capturar_conteudo_site("https://x.com.br") is None

    def test_erro_http_retorna_none(self, monkeypatch):
        import requests
        monkeypatch.setattr(requests, "get", lambda *a, **kw: RespostaFake(status_code=500, text="erro"))
        assert processar.capturar_conteudo_site("https://x.com.br") is None


class TestBuscarInstagramDaEmpresa:
    def _com_resultados(self, monkeypatch, hrefs):
        import ddgs

        class DDGSFake:
            def __init__(self, timeout=None):
                pass

            def text(self, *a, **kw):
                return [{"href": h} for h in hrefs]

        monkeypatch.setattr(ddgs, "DDGS", DDGSFake)

    def test_acha_perfil_valido(self, monkeypatch):
        self._com_resultados(monkeypatch, [
            "https://site-qualquer.com.br/",
            "https://www.instagram.com/clinica_sorriso/",
        ])
        assert (
            processar.buscar_instagram_da_empresa("Clínica Sorriso", "Vitória")
            == "https://www.instagram.com/clinica_sorriso/"
        )

    def test_ignora_links_de_post_e_reel(self, monkeypatch):
        self._com_resultados(monkeypatch, [
            "https://www.instagram.com/p/",
            "https://www.instagram.com/reel/",
        ])
        assert processar.buscar_instagram_da_empresa("Empresa", "") is None

    def test_sem_resultados_retorna_none(self, monkeypatch):
        self._com_resultados(monkeypatch, [])
        assert processar.buscar_instagram_da_empresa("Empresa", "") is None


class TestPipelineComSiteRuim:
    """processar.processar() de ponta a ponta com a rede mockada: site bom é
    descartado, site ruim e sem site viram leads com os campos certos."""

    CABECALHO = "input_id,place_id,title,category,address,review_rating,review_count,phone,website\n"

    def _rodar(self, tmp_path, monkeypatch, linhas_csv, avaliacoes_por_url):
        caminho_csv = tmp_path / "bruto.csv"
        caminho_csv.write_text(self.CABECALHO + linhas_csv, encoding="utf-8")

        monkeypatch.setattr(processar, "CAMINHO_BANCO", tmp_path / "leads.db")
        monkeypatch.setattr(processar, "PASTA_SAIDAS", tmp_path / "saidas")
        monkeypatch.setattr(processar, "buscar_site_da_empresa", lambda nome, endereco="": None)
        monkeypatch.setattr(processar, "buscar_instagram_da_empresa",
                            lambda nome, endereco="": "https://www.instagram.com/achado/")
        monkeypatch.setattr(
            processar, "avaliar_site_completo",
            lambda url: (*avaliacoes_por_url[url], {"tem": ["fotos do negócio"], "falta": ["botão de WhatsApp"]}),
        )

        contagens = processar.processar(caminho_csv, caminho_queries=None)

        import sqlite3
        conexao = sqlite3.connect(tmp_path / "leads.db")
        conexao.row_factory = sqlite3.Row
        leads = {l["place_id"]: dict(l) for l in conexao.execute("SELECT * FROM leads").fetchall()}
        conexao.close()
        return contagens, leads

    def test_classifica_sem_site_site_ruim_e_descarta_site_ok(self, tmp_path, monkeypatch):
        linhas = (
            "i1,p1,Sem Site,cat,end,4.5,10,(41) 98999-0011,\n"
            "i2,p2,Site Ruim,cat,end,4.8,50,(41) 98999-0012,https://ruim.com.br\n"
            "i3,p3,Site Bom,cat,end,5.0,99,(41) 98999-0013,https://bom.com.br\n"
        )
        contagens, leads = self._rodar(tmp_path, monkeypatch, linhas, {
            "https://ruim.com.br": ("ruim", ["não adaptado para celular"]),
            "https://bom.com.br": ("ok", []),
        })

        assert contagens["novos"] == 2
        assert contagens["novos_sem_site"] == 1
        assert contagens["novos_site_ruim"] == 1
        assert contagens["descartados_por_site_ok"] == 1

        assert set(leads) == {"p1", "p2"}  # site bom não entra no CRM
        assert leads["p1"]["site_status"] == "sem_site"
        assert leads["p1"]["site_url"] is None
        assert leads["p2"]["site_status"] == "site_ruim"
        assert leads["p2"]["site_url"] == "https://ruim.com.br"
        assert leads["p2"]["site_problemas"] == "não adaptado para celular"
        assert leads["p1"]["instagram_url"] == "https://www.instagram.com/achado/"

    def test_cidade_padrao_preenche_quando_query_nao_tem_cidade(self, tmp_path, monkeypatch):
        """Busca por mapa: a query é só o nicho, a cidade vem do rótulo do pino."""
        linhas = "i1,p1,Empresa,cat,end,4.5,10,(41) 98999-0011,\n"
        caminho_csv = tmp_path / "bruto.csv"
        caminho_csv.write_text(self.CABECALHO + linhas, encoding="utf-8")
        caminho_queries = tmp_path / "queries.txt"
        caminho_queries.write_text("clínica de estética\n", encoding="utf-8")

        monkeypatch.setattr(processar, "CAMINHO_BANCO", tmp_path / "leads.db")
        monkeypatch.setattr(processar, "PASTA_SAIDAS", tmp_path / "saidas")
        monkeypatch.setattr(processar, "buscar_site_da_empresa", lambda nome, endereco="": None)
        monkeypatch.setattr(processar, "buscar_instagram_da_empresa", lambda nome, endereco="": None)

        processar.processar(
            caminho_csv, caminho_queries=caminho_queries,
            cidade_padrao="Londrina - Paraná", sufixo_saida="_area1",
        )

        import sqlite3
        conexao = sqlite3.connect(tmp_path / "leads.db")
        nicho, cidade = conexao.execute("SELECT nicho, cidade FROM leads").fetchone()
        conexao.close()
        assert nicho == "clínica de estética"
        assert cidade == "Londrina - Paraná"
        # o sufixo evita que áreas diferentes sobrescrevam o mesmo CSV de novos
        assert list((tmp_path / "saidas").glob("leads_novos_*_area1.csv"))

    def test_site_achado_na_busca_web_tambem_e_avaliado(self, tmp_path, monkeypatch):
        linhas = "i1,p1,Empresa,cat,end,4.5,10,(41) 98999-0011,\n"
        caminho_csv = tmp_path / "bruto.csv"
        caminho_csv.write_text(self.CABECALHO + linhas, encoding="utf-8")

        monkeypatch.setattr(processar, "CAMINHO_BANCO", tmp_path / "leads.db")
        monkeypatch.setattr(processar, "PASTA_SAIDAS", tmp_path / "saidas")
        monkeypatch.setattr(processar, "buscar_site_da_empresa",
                            lambda nome, endereco="": "https://escondido.com.br")
        monkeypatch.setattr(processar, "buscar_instagram_da_empresa", lambda nome, endereco="": None)
        monkeypatch.setattr(processar, "avaliar_site_completo",
                            lambda url: ("ruim", ["site fora do ar (não abre)"], None))

        contagens = processar.processar(caminho_csv, caminho_queries=None)

        assert contagens["novos_site_ruim"] == 1
        import sqlite3
        conexao = sqlite3.connect(tmp_path / "leads.db")
        conexao.row_factory = sqlite3.Row
        lead = dict(conexao.execute("SELECT * FROM leads").fetchone())
        conexao.close()
        assert lead["site_url"] == "https://escondido.com.br"
        assert lead["site_status"] == "site_ruim"


class TestDominioEProprio:
    def test_site_proprio_e_aceito(self):
        assert dominio_e_proprio("https://www.minhaempresa.com.br") is True

    def test_site_proprio_sem_www(self):
        assert dominio_e_proprio("https://minhaempresa.com.br/pagina") is True

    def test_facebook_e_rejeitado(self):
        assert dominio_e_proprio("https://facebook.com/empresa") is False

    def test_subdominio_de_rede_social_e_rejeitado(self):
        # este é o bug corrigido: antes só pegava "facebook.com" exato,
        # subdomínios como "blog.facebook.com" ou "m.facebook.com" passavam batendo
        assert dominio_e_proprio("https://blog.facebook.com/empresa") is False
        assert dominio_e_proprio("https://m.facebook.com/empresa") is False

    def test_subdominio_de_agregador_imobiliario_e_rejeitado(self):
        assert dominio_e_proprio("https://www.vivareal.com.br/imovel/123") is False
        assert dominio_e_proprio("https://busca.vivareal.com.br/imovel/123") is False

    def test_url_invalida_e_rejeitada(self):
        assert dominio_e_proprio("") is False
        assert dominio_e_proprio(None) is False


class TestMapearQueriesPorInputId:
    def test_associa_pela_ordem_de_aparicao(self, tmp_path):
        caminho_csv = tmp_path / "bruto.csv"
        caminho_csv.write_text(
            "input_id,title\n"
            "id-1,Empresa A\n"
            "id-1,Empresa B\n"
            "id-2,Empresa C\n",
            encoding="utf-8",
        )
        caminho_queries = tmp_path / "queries.txt"
        caminho_queries.write_text("nicho um\nnicho dois\n", encoding="utf-8")

        resultado = mapear_queries_por_input_id(caminho_csv, caminho_queries)

        assert resultado == {"id-1": "nicho um", "id-2": "nicho dois"}

    def test_arquivo_de_queries_inexistente_retorna_vazio(self, tmp_path):
        caminho_csv = tmp_path / "bruto.csv"
        caminho_csv.write_text("input_id,title\nid-1,Empresa A\n", encoding="utf-8")

        resultado = mapear_queries_por_input_id(caminho_csv, tmp_path / "nao_existe.txt")

        assert resultado == {}


class TestExtrairNichoECidade:
    def test_separa_nicho_e_cidade_com_uf(self):
        assert extrair_nicho_e_cidade("corretor de imóveis em São Francisco MG") == (
            "corretor de imóveis",
            "São Francisco MG",
        )

    def test_separa_nicho_e_cidade_sem_uf(self):
        assert extrair_nicho_e_cidade("clínica de estética em Londrina") == (
            "clínica de estética",
            "Londrina",
        )

    def test_cidade_com_nome_composto(self):
        assert extrair_nicho_e_cidade("arquiteto em Ribeirão Preto") == (
            "arquiteto",
            "Ribeirão Preto",
        )

    def test_usa_ultima_ocorrencia_de_em_como_separador(self):
        # se o nome do nicho tivesse "em" no meio, a ÚLTIMA ocorrência de " em "
        # ainda deve separar corretamente a cidade no final
        assert extrair_nicho_e_cidade("designer de embalagens em Curitiba") == (
            "designer de embalagens",
            "Curitiba",
        )

    def test_sem_padrao_em_retorna_tudo_como_nicho(self):
        assert extrair_nicho_e_cidade("nicho sem cidade") == ("nicho sem cidade", "")

    def test_vazio_retorna_vazio(self):
        assert extrair_nicho_e_cidade("") == ("", "")
        assert extrair_nicho_e_cidade(None) == ("", "")


class TestIndices:
    def test_indices_criados_no_preparar_banco(self):
        import sqlite3
        cx = sqlite3.connect(":memory:")
        processar.preparar_banco(cx)
        indices = {r[0] for r in cx.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
        )}
        # colunas quentes das rotas (filtro/ordenacao) precisam de indice
        for esperado in ("idx_leads_status", "idx_leads_proximo_followup",
                         "idx_leads_site_status", "idx_ig_leads_post_id", "idx_hist_status"):
            assert esperado in indices, f"faltou o indice {esperado}"

    def test_preparar_banco_e_idempotente(self):
        import sqlite3
        cx = sqlite3.connect(":memory:")
        processar.preparar_banco(cx)
        processar.preparar_banco(cx)  # nao pode quebrar rodando de novo
