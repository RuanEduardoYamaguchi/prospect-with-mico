"""Montagem do texto da mensagem: variação por spintax (`{Oi|Olá|Bom dia}`),
variáveis (`{{nome}}`...) e detecção de link pra bloquear no primeiro contato
automático.
"""

import random
import re

from constantes import MARCADOR_PREENCHER

VARIAVEIS_TEMPLATE = re.compile(r"\{\{\s*([\w.-]+)\s*\}\}")
SPINTAX = re.compile(r"\{([^{}]*)\}")

# Trava de segurança do primeiro contato automático: nada de link (é o que
# mais gera denúncia). Envio manual não passa por aqui - lá o link é permitido
# de propósito (ver INTEGRACAO.md).
PADROES_LINK = ("http://", "https://", "www.", ".com", ".com.br", ".br", "wa.me")

# Nome do lead do Maps é o nome do NEGÓCIO ("Clínica Sorriso", "Dra. Fulana
# Odontologia"), não de uma pessoa - diferente do Kaptar, que tem uma coluna
# "Responsável" própria. Sem esse campo aqui, {{primeiro_nome}} só faz sentido
# quando a primeira palavra do nome claramente é um nome próprio (ex: "Dra.
# Fulana"); senão vira vazio, pra não soar "Oi Clínica!".
PREFIXOS_TITULO = {"dr", "dra", "dr.", "dra.", "drs", "drs."}
PALAVRAS_QUE_NAO_SAO_NOME = {
    "clinica", "clínica", "studio", "estúdio", "estudio", "estetica", "estética",
    "espaco", "espaço", "instituto", "centro", "consultorio", "consultório",
    "salao", "salão", "odontologia", "odontológica", "odonto", "clinicas",
    "clínicas", "policlinica", "policlínica",
}


def _escolher(grupo, rand):
    opcoes = grupo.split("|")
    indice = min(int(rand() * len(opcoes)), len(opcoes) - 1)
    return opcoes[indice]


def sortear_variacao(texto, rand=random.random):
    """Resolve `{opção 1|opção 2}` sorteando uma opção a cada chamada - é o
    que faz duas mensagens da mesma campanha nunca saírem idênticas."""
    saida = texto or ""
    guarda = 0
    while "{" in saida and guarda < 50:
        guarda += 1
        antes = saida
        saida = SPINTAX.sub(lambda m: _escolher(m.group(1), rand), saida)
        if saida == antes:
            break
    return saida


def preencher_variaveis(texto, valores):
    """Troca `{{campo}}` pelo valor do dict. Campo ausente ou None vira
    string vazia (nunca quebra o envio por causa de um dado faltando)."""
    def sub(m):
        valor = valores.get(m.group(1).strip())
        return "" if valor is None else str(valor)
    return VARIAVEIS_TEMPLATE.sub(sub, texto or "")


def primeiro_nome(lead):
    """`{{primeiro_nome}}`: usa `lead['responsavel']` quando existe (import do
    Kaptar); sem ele, tenta uma heurística em cima do nome do negócio."""
    responsavel = str(lead.get("responsavel") or "").strip()
    if responsavel:
        limpo = re.sub(r"\(.*?\)", "", responsavel)
        # ordem importa na alternação: "dra"/"drs" tem que vir antes de "dr",
        # senão o regex casa só o prefixo "dr" de "dra" e sobra o "a." solto
        limpo = re.sub(r"\b(dra|drs|dr)\.?\s*", "", limpo, flags=re.IGNORECASE)
        limpo = re.split(r"[,|/]", limpo)[0].strip()
        return limpo.split()[0] if limpo else ""

    nome = str(lead.get("nome") or "").strip()
    if not nome:
        return ""
    palavras = nome.split()
    primeira = re.sub(r"[.,]$", "", palavras[0])

    if primeira.lower().rstrip(".") in PREFIXOS_TITULO and len(palavras) > 1:
        candidata = re.sub(r"[.,]$", "", palavras[1])
        return candidata if candidata[:1].isupper() else ""

    if primeira.lower() in PALAVRAS_QUE_NAO_SAO_NOME:
        return ""
    return primeira if primeira[:1].isupper() else ""


def variaveis_do_lead(lead):
    return {
        "nome": lead.get("nome") or "",
        "primeiro_nome": primeiro_nome(lead),
        "nicho": lead.get("nicho") or "",
        "cidade": lead.get("cidade") or "",
        "nota": lead.get("nota"),
        "avaliacoes": lead.get("num_avaliacoes"),
    }


def montar_mensagem(template, lead, rand=random.random):
    """Variáveis primeiro, variação depois."""
    return sortear_variacao(preencher_variaveis(template, variaveis_do_lead(lead)), rand).strip()


def contem_marcador_preencher(texto):
    """Os modelos prontos trazem "[PREENCHER: seu nome]" pra pessoa trocar pelo
    dado real. Template que ainda tem o marcador não pode virar campanha."""
    return MARCADOR_PREENCHER in (texto or "")


def contem_link(texto):
    """Indício de link no template - regra do primeiro contato automático
    (nunca no primeiro disparo de uma campanha)."""
    minusculo = (texto or "").lower()
    return any(padrao in minusculo for padrao in PADROES_LINK)
