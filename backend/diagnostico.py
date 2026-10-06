"""Diagnóstico de presença digital em PDF - o material que o vendedor manda no
WhatsApp quando a copy promete "posso te enviar um diagnóstico?".

Design: placar visual no topo (reputação + desempenho Google + pontos a corrigir),
problemas em cards numerados com explicação leiga, raio-X em dois painéis
coloridos (tem/falta) e CTA. Determinístico (sem custo de IA). Fontes core do
fpdf2 cobrem latin-1 (acentos pt-BR ok) - nada de emoji/travessão no texto.
"""

import json
import re
from datetime import date

from fpdf import FPDF

import db

# Cores da marca (RGB)
VERDE_ESCURO = (16, 122, 74)
VERDE = (22, 163, 74)
VERDE_FUNDO = (232, 246, 238)
CINZA_TEXTO = (55, 65, 81)
CINZA_SUAVE = (107, 114, 128)
CINZA_CLARO = (243, 244, 246)
CINZA_CARD = (250, 250, 251)
LARANJA = (194, 120, 3)
LARANJA_FUNDO = (253, 243, 224)
VERMELHO = (185, 28, 28)

MARGEM = 12
LARGURA_CONTEUDO = 186

# problema detectado (substring) → (título leigo, explicação do impacto)
EXPLICACOES_PROBLEMAS = [
    ("fora do ar", (
        "O site não abre",
        "Quem clica no site hoje encontra uma página de erro. Cada visita perdida é um cliente "
        "que procurou, não conseguiu ver nada e foi falar com o concorrente.",
    )),
    ("domínio não encontrado", (
        "O endereço do site não existe mais",
        "O domínio parece ter expirado ou sido abandonado. Quem tenta acessar não encontra "
        "nada - é como ter a placa da loja apontando para um terreno vazio.",
    )),
    ("erro (HTTP", (
        "O site responde com erro",
        "O endereço existe, mas devolve uma página de erro em vez do conteúdo. Na prática, "
        "é o mesmo que estar fora do ar para quem visita.",
    )),
    ("SSL", (
        "Certificado de segurança vencido ou inválido",
        "O navegador exibe um alerta de seguranca antes de abrir o site. A maioria das pessoas "
        "desiste nessa tela - e a imagem que fica é de descuido.",
    )),
    ("HTTPS", (
        "Site marcado como 'não seguro'",
        "Sem o cadeado de segurança, Chrome e Safari mostram o aviso 'não seguro' ao lado do "
        "endereço. Isso espanta clientes e derruba a posição no Google.",
    )),
    ("lento", (
        "Site muito lento para carregar",
        "O servidor demora vários segundos só para começar a responder. Na internet, cada segundo "
        "de espera derruba visitas - boa parte das pessoas desiste antes da página abrir.",
    )),
    ("misto", (
        "Página segura carregando itens inseguros",
        "O site tem cadeado, mas puxa imagens ou arquivos por conexão insegura (conteúdo misto). "
        "Navegadores modernos bloqueiam ou alertam sobre isso - partes da página podem nem carregar.",
    )),
    ("celular", (
        "Não adaptado para celular",
        "A grande maioria das pesquisas por negócios locais acontece no celular - e o site "
        "atual não se ajusta à tela. O cliente amplia, aperta o botão errado e desiste.",
    )),
    ("vazia", (
        "Página praticamente vazia",
        "O site existe, mas não apresenta os serviços, fotos ou um botão de contato. "
        "Hoje ele funciona como um cartão de visita em branco.",
    )),
    ("construtor", (
        "Feito em construtor de modelo pronto",
        "O site foi montado numa plataforma de modelos prontos. Funciona, mas tem a mesma cara "
        "de milhares de outros, e não passa a credibilidade que a reputação do negócio merece.",
    )),
    ("atualização", (
        "Site parado no tempo",
        "O rodapé ainda marca um ano antigo - sinal de que o site não recebe atenção há anos. "
        "Para quem visita, parece que o negócio também parou.",
    )),
]

CUSTOS_SEM_SITE = [
    ("Invisível fora do Google Maps", (
        "Quem pesquisa no Google pelo serviço (e não pelo nome) encontra os concorrentes "
        "que têm site - o negócio só aparece para quem já o conhece."
    )),
    ("A reputação não trabalha sozinha", (
        "A nota alta e as avaliações ficam presas no Maps. Um site transforma essa "
        "reputação em página de apresentação, portfólio e canal de contato."
    )),
    ("Sem endereço profissional", (
        "Na hora de fechar, muita gente confere se o negócio 'existe de verdade' na internet. "
        "Sem site, essa confirmação não acontece - e a venda esfria."
    )),
]

PAGESPEED_TIMEOUT_SEGUNDOS = 60  # o PSI roda o Lighthouse de verdade: 15-40s é normal


def consultar_pagespeed(url):
    """Nota oficial de desempenho do Google (PageSpeed Insights, estratégia mobile).
    API gratuita (25k/dia com chave; funciona sem chave para uso leve). Best-effort:
    falha/timeout retorna None e o PDF sai sem a medição. Retorna dict com
    {"nota": 0-100, "tempo_carregamento": "2,5 s" ou None}."""
    import requests

    parametros = {
        "url": url if url.lower().startswith(("http://", "https://")) else f"https://{url}",
        "strategy": "mobile",
        "category": "performance",
    }
    chave = db.obter_config("pagespeed")
    if chave:
        parametros["key"] = chave

    try:
        resposta = requests.get(
            "https://www.googleapis.com/pagespeedonline/v5/runPagespeed",
            params=parametros,
            timeout=PAGESPEED_TIMEOUT_SEGUNDOS,
        )
        if resposta.status_code != 200:
            return None
        dados = resposta.json()
        lighthouse = dados.get("lighthouseResult", {})
        nota_bruta = lighthouse.get("categories", {}).get("performance", {}).get("score")
        if nota_bruta is None:
            return None
        lcp = lighthouse.get("audits", {}).get("largest-contentful-paint", {}).get("displayValue")
        return {"nota": round(nota_bruta * 100), "tempo_carregamento": lcp}
    except Exception:
        return None


def _limpar_latin1(texto):
    """Fontes core do fpdf2 são latin-1: remove o que não codifica (emoji etc.)."""
    return (texto or "").encode("latin-1", "replace").decode("latin-1")


def _cor_nota_pagespeed(nota):
    if nota < 50:
        return VERMELHO
    if nota < 90:
        return LARANJA
    return VERDE


class _PdfDiagnostico(FPDF):
    def header(self):  # noqa: N802 (API do fpdf2)
        self.set_fill_color(*VERDE_ESCURO)
        self.rect(0, 0, 210, 24, style="F")
        self.set_xy(MARGEM, 7)
        self.set_font("helvetica", "B", 16)
        self.set_text_color(255, 255, 255)
        self.cell(130, 10, "Diagnóstico de presença digital")
        self.set_font("helvetica", "", 9)
        self.set_text_color(220, 240, 230)
        self.cell(0, 10, date.today().strftime("%d/%m/%Y"), align="R")


def _titulo_secao(pdf, texto):
    pdf.set_font("helvetica", "B", 12)
    pdf.set_text_color(*CINZA_TEXTO)
    pdf.cell(0, 7, _limpar_latin1(texto), new_x="LMARGIN", new_y="NEXT")
    pdf.set_fill_color(*VERDE)
    pdf.rect(MARGEM, pdf.get_y() + 0.5, 14, 1.1, style="F")
    pdf.ln(5)


def _tile(pdf, x, y, largura, rotulo, valor, cor_valor, subtitulo=None, fracao_barra=None):
    """Um bloco do placar: rótulo pequeno, valor grande colorido, barra opcional."""
    altura = 27
    pdf.set_fill_color(*CINZA_CLARO)
    pdf.rect(x, y, largura, altura, style="F", round_corners=True, corner_radius=2)

    pdf.set_xy(x + 4, y + 3.5)
    pdf.set_font("helvetica", "B", 6.8)
    pdf.set_text_color(*CINZA_SUAVE)
    pdf.cell(largura - 8, 3.4, _limpar_latin1(rotulo.upper()))

    pdf.set_xy(x + 4, y + 8)
    pdf.set_font("helvetica", "B", 15)
    pdf.set_text_color(*cor_valor)
    pdf.cell(largura - 8, 7, _limpar_latin1(valor))

    y_sub = y + 16.5
    if fracao_barra is not None:
        pdf.set_fill_color(224, 227, 231)
        pdf.rect(x + 4, y_sub, largura - 8, 1.8, style="F", round_corners=True, corner_radius=0.9)
        pdf.set_fill_color(*cor_valor)
        pdf.rect(
            x + 4, y_sub, max((largura - 8) * min(max(fracao_barra, 0), 1), 1.5), 1.8,
            style="F", round_corners=True, corner_radius=0.9,
        )
        y_sub += 3.4

    if subtitulo:
        pdf.set_xy(x + 4, y_sub)
        pdf.set_font("helvetica", "", 6.8)
        pdf.set_text_color(*CINZA_SUAVE)
        pdf.multi_cell(largura - 8, 3.1, _limpar_latin1(subtitulo))

    return altura


def _card_problema(pdf, numero, titulo, explicacao):
    """Card com fundo suave, faixa lateral laranja, número em círculo e texto."""
    x, largura = MARGEM, LARGURA_CONTEUDO
    largura_texto = largura - 14
    linhas = pdf.multi_cell(
        largura_texto, 4.3, _limpar_latin1(explicacao), dry_run=True, output="LINES"
    )
    altura = 8.5 + len(linhas) * 4.3 + 2.5
    y = pdf.get_y()

    pdf.set_fill_color(*CINZA_CARD)
    pdf.rect(x, y, largura, altura, style="F", round_corners=True, corner_radius=2)
    pdf.set_fill_color(*LARANJA)
    pdf.rect(x, y, 1.6, altura, style="F")

    # círculo com o número
    pdf.set_fill_color(*LARANJA)
    pdf.ellipse(x + 4.5, y + 2.6, 5.4, 5.4, style="F")
    pdf.set_xy(x + 4.5, y + 3.6)
    pdf.set_font("helvetica", "B", 8)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(5.4, 3.4, str(numero), align="C")

    pdf.set_xy(x + 12, y + 3)
    pdf.set_font("helvetica", "B", 10.5)
    pdf.set_text_color(*CINZA_TEXTO)
    pdf.cell(largura - 16, 5, _limpar_latin1(titulo))

    pdf.set_xy(x + 12, y + 8.5)
    pdf.set_font("helvetica", "", 9)
    pdf.set_text_color(*CINZA_SUAVE)
    pdf.multi_cell(largura_texto, 4.3, _limpar_latin1(explicacao))

    pdf.set_y(y + altura + 3)


def _painel_lista(pdf, x, y, largura, titulo, cor_titulo, cor_fundo, prefixo, itens):
    """Painel colorido do raio-X (uma coluna: 'já tem' ou 'faltando')."""
    linhas = max(len(itens), 1)
    altura = 9 + linhas * 4.6 + 2
    pdf.set_fill_color(*cor_fundo)
    pdf.rect(x, y, largura, altura, style="F", round_corners=True, corner_radius=2)

    pdf.set_xy(x + 4, y + 2.8)
    pdf.set_font("helvetica", "B", 7.5)
    pdf.set_text_color(*cor_titulo)
    pdf.cell(largura - 8, 4, _limpar_latin1(titulo.upper()))

    pdf.set_font("helvetica", "", 8.7)
    pdf.set_text_color(*CINZA_TEXTO)
    y_item = y + 8.2
    for item in itens or ["nada detectado"]:
        pdf.set_xy(x + 4, y_item)
        pdf.cell(largura - 8, 4.6, _limpar_latin1(f"{prefixo} {item}"))
        y_item += 4.6

    return altura


def gerar_diagnostico_pdf(lead):
    """Gera o PDF de diagnóstico de um lead (dict/Row com os campos de leads).
    Retorna os bytes do arquivo."""
    tem_site = lead["site_status"] == "site_ruim"
    problemas_texto = (lead["site_problemas"] or "") if tem_site else ""

    # ---- coleta de dados antes de desenhar ----
    checklist = None
    if tem_site:
        try:
            checklist = json.loads(lead["site_checklist"]) if lead["site_checklist"] else None
        except (TypeError, ValueError, KeyError, IndexError):
            checklist = None

    pagespeed = consultar_pagespeed(lead["site_url"]) if (tem_site and lead["site_url"]) else None

    if tem_site:
        achados = [
            (titulo, explicacao)
            for chave, (titulo, explicacao) in EXPLICACOES_PROBLEMAS
            if chave.lower() in problemas_texto.lower()
        ] or [(
            "Site com problemas técnicos",
            problemas_texto or "Problemas técnicos detectados na análise automática.",
        )]
    else:
        achados = CUSTOS_SEM_SITE

    # ---- desenho ----
    pdf = _PdfDiagnostico(format="A4")
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()

    # Identificação do negócio
    pdf.set_y(31)
    pdf.set_text_color(*CINZA_TEXTO)
    pdf.set_font("helvetica", "B", 15)
    pdf.cell(0, 8, _limpar_latin1(lead["nome"] or ""), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 9.5)
    pdf.set_text_color(*CINZA_SUAVE)
    subtitulo = " - ".join(p for p in [lead["categoria"], lead["cidade"]] if p)
    pdf.cell(0, 5.5, _limpar_latin1(subtitulo), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Placar: 3 tiles lado a lado
    nota = lead["nota"] or 0
    avaliacoes = lead["num_avaliacoes"] or 0
    y_placar = pdf.get_y()
    largura_tile = (LARGURA_CONTEUDO - 8) / 3

    _tile(
        pdf, MARGEM, y_placar, largura_tile,
        "Reputação no Google", f"{nota}", VERDE_ESCURO,
        subtitulo=f"{avaliacoes} avaliações de clientes",
        fracao_barra=(nota / 5) if nota else 0,
    )

    x2 = MARGEM + largura_tile + 4
    if not tem_site:
        _tile(pdf, x2, y_placar, largura_tile, "Site próprio", "Não tem", VERMELHO,
              subtitulo="nenhum site encontrado no Google")
    elif pagespeed:
        detalhe = (
            f"conteúdo aparece em {pagespeed['tempo_carregamento']} no celular"
            if pagespeed["tempo_carregamento"] else "medição oficial do Google (PageSpeed)"
        )
        _tile(
            pdf, x2, y_placar, largura_tile,
            "Desempenho (Google PageSpeed)", f"{pagespeed['nota']}/100",
            _cor_nota_pagespeed(pagespeed["nota"]),
            subtitulo=detalhe, fracao_barra=pagespeed["nota"] / 100,
        )
    else:
        _tile(pdf, x2, y_placar, largura_tile, "Desempenho (Google PageSpeed)", "-",
              CINZA_SUAVE, subtitulo="medição indisponível agora")

    x3 = MARGEM + (largura_tile + 4) * 2
    rotulo3 = "Pontos a corrigir" if tem_site else "Oportunidades perdidas"
    _tile(pdf, x3, y_placar, largura_tile, rotulo3, str(len(achados)), LARANJA,
          subtitulo="detalhados abaixo")

    pdf.set_y(y_placar + 27 + 7)

    # Achados em cards numerados
    _titulo_secao(
        pdf, "O que encontramos no site atual" if tem_site else "O que a ausência de site está custando"
    )
    for numero, (titulo, explicacao) in enumerate(achados, start=1):
        _card_problema(pdf, numero, titulo, explicacao)

    # Raio-X em dois painéis coloridos
    if checklist and (checklist.get("tem") or checklist.get("falta")):
        pdf.ln(2)
        _titulo_secao(pdf, "Raio-X do site atual")
        largura_painel = (LARGURA_CONTEUDO - 4) / 2
        y_paineis = pdf.get_y()
        altura_esq = _painel_lista(
            pdf, MARGEM, y_paineis, largura_painel,
            "O que o site já tem", VERDE_ESCURO, VERDE_FUNDO, "+", (checklist.get("tem") or [])[:9],
        )
        altura_dir = _painel_lista(
            pdf, MARGEM + largura_painel + 4, y_paineis, largura_painel,
            "O que está faltando", LARANJA, LARANJA_FUNDO, "-",
            (checklist.get("falta") or ["nada - estrutura completa"])[:9],
        )
        pdf.set_y(y_paineis + max(altura_esq, altura_dir) + 4)

    if tem_site and lead["site_url"]:
        pdf.set_font("helvetica", "I", 8)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(0, 5, _limpar_latin1(f"Análise automática de {lead['site_url']}"),
                 new_x="LMARGIN", new_y="NEXT")

    # Proposta / CTA - assinada pelo vendedor, como uma mensagem pessoal
    nome_vendedor = db.obter_config("vendedor_nome")

    pdf.ln(3)
    y_cta = pdf.get_y()
    altura_cta = 24 if nome_vendedor else 21
    pdf.set_fill_color(*VERDE_ESCURO)
    pdf.rect(MARGEM, y_cta, LARGURA_CONTEUDO, altura_cta, style="F", round_corners=True, corner_radius=2)
    pdf.set_xy(MARGEM + 6, y_cta + 4)
    pdf.set_font("helvetica", "B", 11)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 6, "O próximo passo é simples", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(MARGEM + 6)
    pdf.set_font("helvetica", "", 9.5)
    pdf.cell(0, 5, "Posso preparar uma prévia de como ficaria o site - sem compromisso. É só responder esta mensagem.",
             new_x="LMARGIN", new_y="NEXT")
    if nome_vendedor:
        pdf.set_xy(MARGEM + 6, y_cta + altura_cta - 8)
        pdf.set_font("helvetica", "I", 9.5)
        pdf.set_text_color(220, 240, 230)
        pdf.cell(LARGURA_CONTEUDO - 12, 5, _limpar_latin1(f"- {nome_vendedor}"), align="R")
    pdf.set_y(y_cta + altura_cta)

    return bytes(pdf.output())


def nome_arquivo_diagnostico(nome_lead):
    base = re.sub(r"[^A-Za-z0-9]+", "-", nome_lead or "lead").strip("-").lower() or "lead"
    return f"diagnostico-{base}.pdf"
