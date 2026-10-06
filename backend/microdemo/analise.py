"""Análise de oportunidade: uma IA faz o papel de analista comercial, acha UMA
oportunidade verificável na jornada do lead e escolhe um modelo de micro-demo
do catálogo. O resultado fica salvo em `analises_oportunidade` e só é refeito
quando alguém pede.
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path

import db
import ia
import processar
import rotas_leads
from microdemo.catalogo import CATALOGO

logger = logging.getLogger(__name__)

CAMINHO_PROMPT = Path(__file__).parent.parent / "prompt_analista.md"
CHAVE_SCORE_MIN = "analise_score_min"
SCORE_MIN_PADRAO = 70
MAX_TOKENS_ANALISE = 1400

MAX_CHARS_CAMPO = 600
MAX_ITENS_LISTA = 6
MAX_CHARS_ITEM = 300

RECOMENDACOES = ("abordar_com_demo", "abordar_sem_demo", "nao_abordar")
CONFIANCAS = ("alta", "media", "baixa")
CAMPOS_TEXTO = ("oportunidade", "impacto", "solucao", "motivo_nao_abordar", "angulo")
CAMPOS_LISTA = ("evidencias", "desconhecido")

NAO_VERIFICAVEL = (
    "conteúdo do Instagram (posts, frequência, qualidade)",
    "como o negócio atende por telefone",
    "se aceita encaixe ou atendimento sem hora marcada",
    "detalhes do perfil do Google além de nota e número de avaliações "
    "(fotos, horários, respostas a avaliações, botões de agendar ou pedir)",
)


class ScoreAbaixoDoMinimo(Exception):
    def __init__(self, score, minimo):
        super().__init__(f"score {score} abaixo do mínimo {minimo}")
        self.score = score
        self.minimo = minimo


# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

def score_minimo():
    try:
        return int(db.obter_config(CHAVE_SCORE_MIN))
    except (TypeError, ValueError):
        return SCORE_MIN_PADRAO


def salvar_score_minimo(valor):
    if isinstance(valor, bool) or not isinstance(valor, int) or not 0 <= valor <= 100:
        raise ValueError("o score mínimo deve ser um número inteiro entre 0 e 100")
    db.salvar_config(CHAVE_SCORE_MIN, str(valor))


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

def _ler_prompt():
    try:
        return CAMINHO_PROMPT.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def montar_system():
    """O .md é editável; o catálogo e o contrato JSON ficam no
    código pra que editar o texto nunca quebre o parser."""
    catalogo = "\n".join(
        f'- "{chave}": {item["descricao"]}. Use quando: {item["quando_usar"]}.'
        for chave, item in CATALOGO.items()
    )
    chaves = " | ".join(f'"{c}"' for c in (*CATALOGO, "nenhuma"))
    return f"""{_ler_prompt()}

Modelos de micro-demo disponíveis:
{catalogo}
- "nenhuma": nenhum dos modelos acima resolve a oportunidade encontrada.

Responda APENAS um objeto JSON, sem texto antes ou depois, com exatamente estas chaves:
{{
  "recomendacao": "abordar_com_demo" | "abordar_sem_demo" | "nao_abordar",
  "oportunidade": "a principal oportunidade, em uma ou duas frases",
  "evidencias": ["cada evidência cita a fonte: site, Google, raio-X ou sinais"],
  "impacto": "impacto potencial",
  "solucao": "solução recomendada",
  "micro_demo": {chaves},
  "confianca": "alta" | "media" | "baixa",
  "motivo_nao_abordar": "preencha se a oportunidade for fraca, senão string vazia",
  "desconhecido": ["o que não pôde ser verificado"],
  "angulo": "uma frase com o ângulo da abordagem"
}}"""


def _linha(rotulo, valor):
    return f"- {rotulo}: {valor if valor not in (None, '') else 'desconhecido'}"


def _checklist(lead):
    bruto = lead.get("site_checklist")
    if not bruto:
        return None
    try:
        dados = json.loads(bruto)
    except (TypeError, ValueError):
        return None
    return dados if isinstance(dados, dict) else None


def montar_user(lead, resumo_site, sinais, score):
    linhas = ["Dados do Google:"]
    linhas += [
        _linha("nome", lead.get("nome")),
        _linha("categoria", lead.get("categoria")),
        _linha("nicho", lead.get("nicho")),
        _linha("cidade", lead.get("cidade")),
        _linha("nota", lead.get("nota")),
        _linha("número de avaliações", lead.get("num_avaliacoes")),
    ]

    linhas += ["", "Site:"]
    linhas += [
        _linha("endereço", lead.get("site_url") or "sem site"),
        _linha("situação", lead.get("site_status")),
        _linha("problemas encontrados", lead.get("site_problemas")),
    ]
    checklist = _checklist(lead)
    if checklist:
        linhas.append(_linha("raio-X, o site tem", ", ".join(checklist.get("tem") or []) or "nada listado"))
        linhas.append(_linha("raio-X, o site não tem", ", ".join(checklist.get("falta") or []) or "nada listado"))
    linhas.append("- conteúdo do site:\n" + (resumo_site or "não foi possível ler o site"))

    linhas += ["", "Sinais de conversão procurados no HTML do site:"]
    linhas.append(_linha("encontrados", "; ".join(sinais["encontrados"]) or "nenhum"))
    linhas.append(_linha("procurados e não encontrados", "; ".join(sinais["nao_encontrados"]) or "nenhum"))

    linhas += ["", "Outros dados:"]
    linhas.append(_linha("tem Instagram cadastrado", "sim" if lead.get("instagram_url") else "não"))
    linhas.append(_linha("score de oportunidade (0 a 100)", score))

    linhas += ["", "O sistema NÃO consegue verificar (marque como desconhecido, nunca invente):"]
    linhas += [f"- {item}" for item in NAO_VERIFICAVEL]
    return "\n".join(linhas)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def _texto(valor):
    if valor is None:
        return ""
    return str(valor).strip()[:MAX_CHARS_CAMPO]


def _lista(valor):
    if isinstance(valor, str):
        valor = [valor]
    if not isinstance(valor, list):
        return []
    itens = [str(item).strip()[:MAX_CHARS_ITEM] for item in valor if str(item).strip()]
    return itens[:MAX_ITENS_LISTA]


def _parsear(resposta_bruta):
    texto = (resposta_bruta or "").strip()
    texto = re.sub(r"^```(?:json)?\s*|\s*```$", "", texto, flags=re.IGNORECASE).strip()
    dados = json.loads(texto)  # JSON inválido levanta e o fallback tenta o próximo provedor
    if not isinstance(dados, dict):
        raise ValueError("a resposta da análise não é um objeto JSON")

    recomendacao = dados.get("recomendacao")
    micro_demo = dados.get("micro_demo")
    confianca = dados.get("confianca")
    resultado = {
        "recomendacao": recomendacao if recomendacao in RECOMENDACOES else "nao_abordar",
        "micro_demo": micro_demo if micro_demo in CATALOGO else "nenhuma",
        "confianca": confianca if confianca in CONFIANCAS else "baixa",
    }
    for campo in CAMPOS_TEXTO:
        resultado[campo] = _texto(dados.get(campo))
    for campo in CAMPOS_LISTA:
        resultado[campo] = _lista(dados.get(campo))
    return resultado


# ---------------------------------------------------------------------------
# Execução e persistência
# ---------------------------------------------------------------------------

def carregar_lead(place_id):
    conexao = db.conectar()
    try:
        linha = conexao.execute("SELECT * FROM leads WHERE place_id = ?", (place_id,)).fetchone()
    finally:
        conexao.close()
    return dict(linha) if linha else None


def calcular_score_do_lead(lead):
    return rotas_leads.calcular_score(
        lead.get("nota"), lead.get("num_avaliacoes"), lead.get("site_status"),
        site_problemas=lead.get("site_problemas"),
        instagram_url=lead.get("instagram_url"),
        nicho=lead.get("nicho"),
    )


def _linha_para_analise(linha):
    analise = dict(linha)
    for campo in CAMPOS_LISTA:
        try:
            analise[campo] = json.loads(analise.get(campo) or "[]")
        except ValueError:
            analise[campo] = []
    analise.pop("place_id", None)
    return analise


def ultima_analise(place_id):
    conexao = db.conectar()
    try:
        linha = conexao.execute(
            "SELECT * FROM analises_oportunidade WHERE place_id = ? ORDER BY id DESC LIMIT 1",
            (place_id,),
        ).fetchone()
    finally:
        conexao.close()
    return _linha_para_analise(linha) if linha else None


def analisar(place_id):
    lead = carregar_lead(place_id)
    if lead is None:
        raise LookupError(place_id)

    score = calcular_score_do_lead(lead)
    minimo = score_minimo()
    if score < minimo:
        raise ScoreAbaixoDoMinimo(score, minimo)

    resumo_site = None
    sinais = {
        "encontrados": [],
        "nao_encontrados": ["agendamento online", "pedido ou cardápio online", "formulário de contato"],
    }
    if lead.get("site_url"):
        html = processar._baixar_html(lead["site_url"])
        if html is not None:
            resumo_site = processar.resumir_conteudo(html)
            sinais = processar.extrair_sinais_conversao(html)

    nome = lead.get("nome") or place_id
    resultado, provedor, avisos = ia.executar_com_fallback(
        montar_system(),
        montar_user(lead, resumo_site, sinais, score),
        parser=_parsear,
        descricao_log=f"analisar oportunidade de {nome}",
        temperatura=ia.TEMPERATURA_CLASSIFICACAO,
        formato_json=True,
        max_tokens=MAX_TOKENS_ANALISE,
    )

    criada_em = datetime.now().isoformat(timespec="seconds")
    conexao = db.conectar()
    try:
        cursor = conexao.execute(
            "INSERT INTO analises_oportunidade (place_id, recomendacao, oportunidade, evidencias, "
            "impacto, solucao, micro_demo, confianca, motivo_nao_abordar, desconhecido, angulo, "
            "score_no_momento, provedor, criada_em) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                place_id, resultado["recomendacao"], resultado["oportunidade"],
                json.dumps(resultado["evidencias"], ensure_ascii=False),
                resultado["impacto"], resultado["solucao"], resultado["micro_demo"],
                resultado["confianca"], resultado["motivo_nao_abordar"],
                json.dumps(resultado["desconhecido"], ensure_ascii=False),
                resultado["angulo"], score, provedor, criada_em,
            ),
        )
        conexao.commit()
        analise_id = cursor.lastrowid
    finally:
        conexao.close()

    return {"id": analise_id, **resultado, "score_no_momento": score,
            "provedor": provedor, "avisos": avisos, "criada_em": criada_em}
