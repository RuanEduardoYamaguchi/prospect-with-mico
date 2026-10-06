"""Importa uma lista de contatos (CSV do Kaptar ou "Nome, telefone" por linha)
pro CRM de leads desta ferramenta.

O parser faz detecção de separador, normalização de nome de coluna, aceita os
dois formatos de export do Kaptar (leads e ativos) e o formato simples
"Nome, telefone" por linha.

O campo bruto da coluna (ex.: "tem_site" = "Sim"/"Não") e o booleano derivado
convivem - o booleano fica em `tem_site_bool`/`tem_instagram_bool`
e o texto bruto continua em `tem_site`/`tem_instagram` - porque o mapeamento
pra `leads.site_status` precisa do valor explícito da coluna (sim/não/ausente
são três coisas diferentes), não só de um sim-ou-não já achatado.
"""

import logging
import re
import sqlite3
import unicodedata
from collections import Counter
from datetime import datetime

import rotas_conversa

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Normalização de telefone (porta de normalizarNumero/ehCelular do lib.js)
# ---------------------------------------------------------------------------


def normalizar_numero(bruto):
    """Telefone brasileiro só-dígitos com DDI 55 (mesmo formato que a Evolution
    API espera). None quando o número não dá pra usar - mesma regra do painel
    Node antigo (lib.js `normalizarNumero`)."""
    if not bruto:
        return None
    digitos = re.sub(r"\D", "", str(bruto))
    if digitos.startswith("00"):
        digitos = digitos[2:]
    if len(digitos) in (10, 11):
        digitos = "55" + digitos
    if not digitos.startswith("55"):
        return digitos if 11 <= len(digitos) <= 15 else None
    nacional = digitos[2:]
    if len(nacional) not in (10, 11):
        return None
    ddd = int(nacional[:2])
    if ddd < 11 or ddd > 99:
        return None
    return digitos


def _e_celular(numero_com_ddi):
    """Nono dígito presente = celular, não fixo - mesma regra do lib.js `ehCelular`."""
    nacional = re.sub(r"^55", "", str(numero_com_ddi or ""))
    return len(nacional) == 11 and nacional[2] == "9"


def _e_sim(valor):
    """"Sim" ou "S" (com ou sem acento/maiúscula) - mesma regra do lib.js `ehSim`."""
    return bool(re.match(r"^s(im)?$", str(valor or "").strip(), re.IGNORECASE))


def _numero_ou_nulo(valor):
    texto = str(valor if valor is not None else "").strip().replace(",", ".")
    if not texto:
        return None
    try:
        return float(texto)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Leitura do CSV (porta de lerCSV/lerContatos do lib.js)
# ---------------------------------------------------------------------------


def _achar_separador(linha):
    """Descobre o separador olhando só o que está fora das aspas - mesma regra
    do lib.js `acharSeparador`."""

    def contar(caractere):
        dentro = False
        total = 0
        for c in linha:
            if c == '"':
                dentro = not dentro
            elif c == caractere and not dentro:
                total += 1
        return total

    candidatos = [(";", contar(";")), ("\t", contar("\t")), (",", contar(","))]
    candidatos.sort(key=lambda par: par[1], reverse=True)
    return candidatos[0][0] if candidatos[0][1] > 0 else ";"


def ler_csv(texto_bruto):
    """Parser de CSV com aspas, do jeito que o Kaptar exporta: campos entre
    aspas, separador detectado automaticamente (`;`, tab ou `,`) e aspas dupla
    escapada dobrando (""). Mesma lógica do lib.js `lerCSV`, incluindo o
    descarte do BOM no início do arquivo."""
    texto = str(texto_bruto or "")
    if texto.startswith("﻿"):
        texto = texto[1:]

    primeira_linha = re.split(r"\r?\n", texto, maxsplit=1)[0] if texto else ""
    separador = _achar_separador(primeira_linha)

    linhas = []
    campo = ""
    linha = []
    dentro = False
    i = 0
    total = len(texto)
    while i < total:
        c = texto[i]
        if dentro:
            if c == '"':
                if i + 1 < total and texto[i + 1] == '"':
                    campo += '"'
                    i += 2
                    continue
                dentro = False
                i += 1
                continue
            campo += c
            i += 1
            continue
        if c == '"':
            dentro = True
            i += 1
            continue
        if c == separador:
            linha.append(campo)
            campo = ""
            i += 1
            continue
        if c == "\r":
            i += 1
            continue
        if c == "\n":
            linha.append(campo)
            linhas.append(linha)
            linha = []
            campo = ""
            i += 1
            continue
        campo += c
        i += 1
    if campo != "" or linha:
        linha.append(campo)
        linhas.append(linha)

    return [l for l in linhas if any(str(celula).strip() != "" for celula in l)]


def _chave_de_coluna(nome):
    """Nome de coluna sem acento, minúsculo, com underscore - mesma regra do
    lib.js `chaveDeColuna`."""
    texto = str(nome or "").strip().lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^a-z0-9]+", "_", texto)
    return texto.strip("_")


# Colunas do Kaptar (e variações) traduzidas pros campos internos. Os dois
# exports do Kaptar têm cabeçalho diferente: um traz "Nicho", "WhatsApp
# provável" e "Responsável"; o outro traz "Categoria", "Tem Instagram",
# "Status" e "Tipo".
APELIDOS = {
    "nome": "nome", "empresa": "nome", "estabelecimento": "nome", "razao_social": "nome",
    "telefone": "telefone", "fone": "telefone", "celular": "telefone", "whatsapp": "telefone",
    "whatsapp_provavel": "whatsapp_provavel",
    "nicho": "nicho", "categoria": "nicho", "segmento": "nicho",
    "site": "site", "tem_site": "tem_site",
    "instagram": "instagram", "tem_instagram": "tem_instagram",
    "e_mail": "email", "email": "email",
    "facebook": "facebook",
    "responsavel": "responsavel", "contato": "responsavel",
    "resumo": "resumo", "descricao": "resumo",
    "cidade": "cidade", "estado": "estado",
    "score": "score",
    "avaliacao": "avaliacao", "nota": "avaliacao",
    "no_avaliacoes": "avaliacoes", "n_avaliacoes": "avaliacoes", "numero_de_avaliacoes": "avaliacoes",
    "status": "status", "tipo": "tipo",
    "fonte": "fonte", "google_maps": "google_maps",
    "encontrado_em": "encontrado_em", "criado_em": "encontrado_em",
}


def _primeiro_nome(responsavel):
    """Primeiro nome de quem responde, pra usar como {{primeiro_nome}} na
    mensagem - mesma regra do lib.js `primeiroNome`.

    Diferença proposital: a alternativa da regex de título fica em ordem
    "dra|drs|dr" (mais específica primeiro), não "dr|dra|drs" como no
    original. Regex de alternância casa a primeira opção que bate, não a
    mais longa - com a ordem do lib.js, "Dra." casava só o "Dr" e sobrava um
    "a." grudado no nome (virava primeiro_nome "a." em vez de "Ana")."""
    limpo = re.sub(r"\(.*?\)", "", str(responsavel or ""))
    limpo = re.sub(r"\b(dra|drs|dr)\.?\s*", "", limpo, flags=re.IGNORECASE)
    limpo = re.split(r"[,|/]", limpo)[0].strip()
    return limpo.split()[0] if limpo else ""


def _parece_cabecalho(colunas_normalizadas, primeira_linha_bruta):
    tem_apelido = any(coluna in APELIDOS for coluna in colunas_normalizadas)
    tem_numero_longo = any(
        len(re.sub(r"\D", "", str(celula))) >= 8 for celula in primeira_linha_bruta
    )
    return tem_apelido and not tem_numero_longo


def ler_contatos(texto_bruto):
    """Lê a lista colada ou o CSV do Kaptar (os dois formatos de export) ou o
    formato simples de uma linha por contato ("Clínica Sorriso,
    41999999999"). Retorna (contatos, invalidos) - `invalidos` tem um dict
    {linha, motivo} por registro descartado (telefone inválido ou repetido),
    pra quem chama poder contar por motivo."""
    linhas = ler_csv(texto_bruto)
    if not linhas:
        return [], []

    colunas = [_chave_de_coluna(c) for c in linhas[0]]
    brutos = []

    if _parece_cabecalho(colunas, linhas[0]):
        for linha in linhas[1:]:
            registro = {}
            for i, coluna in enumerate(colunas):
                campo = APELIDOS.get(coluna, coluna)
                valor = str(linha[i] if i < len(linha) else "").strip()
                if campo and valor != "":
                    registro[campo] = valor
            brutos.append(registro)
    else:
        for linha in linhas:
            partes = [str(p).strip() for p in linha]
            if len(partes) == 1:
                brutos.append({"telefone": partes[0]})
                continue
            indice_fone = next(
                (i for i, p in enumerate(partes) if len(re.sub(r"\D", "", p)) >= 10), None
            )
            if indice_fone is None:
                nome = " ".join(partes).strip()
                telefone = partes[-1]
            else:
                nome = " ".join(p for i, p in enumerate(partes) if i != indice_fone).strip()
                telefone = partes[indice_fone]
            brutos.append({"nome": nome, "telefone": telefone})

    contatos = []
    invalidos = []
    vistos = set()
    for registro in brutos:
        numero = normalizar_numero(registro.get("telefone"))
        rotulo = registro.get("nome") or registro.get("telefone") or "(linha vazia)"
        if not numero:
            invalidos.append({"linha": rotulo, "motivo": "telefone inválido"})
            continue
        if numero in vistos:
            invalidos.append({"linha": registro.get("nome") or numero, "motivo": "número repetido na lista"})
            continue
        vistos.add(numero)

        contato = dict(registro)
        contato["numero"] = numero
        contato["nome"] = (registro.get("nome") or "").strip()
        contato["primeiro_nome"] = _primeiro_nome(registro.get("responsavel"))
        contato["nicho"] = registro.get("nicho") or ""
        contato["cidade"] = registro.get("cidade") or ""
        contato["tem_site_bool"] = (
            _e_sim(registro["tem_site"]) if registro.get("tem_site") else bool(registro.get("site"))
        )
        contato["tem_instagram_bool"] = (
            _e_sim(registro["tem_instagram"]) if registro.get("tem_instagram") else bool(registro.get("instagram"))
        )
        contato["whatsapp_provavel_bool"] = (
            _e_sim(registro["whatsapp_provavel"]) if registro.get("whatsapp_provavel") else _e_celular(numero)
        )
        contato["score_num"] = _numero_ou_nulo(registro.get("score"))
        contato["avaliacao_num"] = _numero_ou_nulo(registro.get("avaliacao"))
        contato["avaliacoes_num"] = _numero_ou_nulo(registro.get("avaliacoes"))
        contatos.append(contato)

    return contatos, invalidos


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


def preparar(conexao):
    """Migração aditiva: `leads.origem TEXT` ('maps' | 'kaptar'). Idempotente -
    segura rodar toda vez que o banco abre, igual às migrações de
    `processar.migrar_banco`. Leads que já existiam antes desta coluna vieram
    todos do Maps, então o backfill é 'maps'."""
    colunas = {linha[1] for linha in conexao.execute("PRAGMA table_info(leads)")}
    if "origem" not in colunas:
        conexao.execute("ALTER TABLE leads ADD COLUMN origem TEXT")
    conexao.execute("UPDATE leads SET origem = 'maps' WHERE origem IS NULL")
    conexao.commit()


# ---------------------------------------------------------------------------
# Import pra tabela leads
# ---------------------------------------------------------------------------


def _linha_para_dict(cursor, linha):
    if linha is None:
        return None
    if isinstance(linha, sqlite3.Row):
        return dict(linha)
    colunas = [d[0] for d in cursor.description]
    return dict(zip(colunas, linha))


def _achar_lead_por_telefone(conexao, telefone_bruto):
    """Procura um lead já existente com o mesmo telefone, comparando todas as
    variações do nono dígito (`rotas_conversa._variantes_telefone` - a mesma
    função que liga a captura do WhatsApp ao lead certo). Retorna o lead como
    dict, ou None."""
    variantes = rotas_conversa._variantes_telefone(telefone_bruto)
    if not variantes:
        return None

    cursor = conexao.execute("SELECT * FROM leads WHERE telefone IS NOT NULL AND telefone != ''")
    for linha in cursor.fetchall():
        registro = _linha_para_dict(cursor, linha)
        if rotas_conversa._variantes_telefone(registro.get("telefone")) & variantes:
            return registro
    return None


def _mapear_site_status(tem_site_bruto):
    """Tri-estado explícito a partir da coluna "Tem site": só assume
    sem_site/site_ok quando a coluna diz claramente sim ou não. Ambíguo ou
    ausente vira None (fica em branco) - a migração de `processar.migrar_banco`
    já faz o backfill de site_status NULL pra 'sem_site', então não é preciso
    (nem seguro) adivinhar aqui um valor que a lista não confirma."""
    valor = str(tem_site_bruto or "").strip().lower()
    if valor in ("sim", "s"):
        return "site_ok"
    if valor in ("não", "nao", "n"):
        return "sem_site"
    return None


def _preparar_campos(contato):
    numero = contato["numero"]
    telefone = numero[2:] if numero.startswith("55") else numero  # forma canônica sem DDI, igual ao Maps
    whatsapp_link = f"https://wa.me/{numero}"

    tags_extra = []
    if _e_sim(contato.get("tem_instagram")):
        # sem URL real pra não inventar um perfil que pode nem existir -
        # a confirmação do Kaptar vira uma tag, não um instagram_url falso
        tags_extra.append("instagram (kaptar)")

    partes_observacoes = []
    if contato.get("resumo"):
        partes_observacoes.append(f"Resumo (Kaptar): {contato['resumo']}")
    if contato.get("responsavel"):
        partes_observacoes.append(f"Responsável: {contato['responsavel']}")
    if contato.get("status"):
        partes_observacoes.append(f"Status no Kaptar: {contato['status']}")
    if contato.get("tipo"):
        partes_observacoes.append(f"Tipo: {contato['tipo']}")

    return {
        "telefone": telefone,
        "whatsapp_link": whatsapp_link,
        "nicho": (contato.get("nicho") or "").strip() or None,
        "cidade": (contato.get("cidade") or "").strip() or None,
        "site_status": _mapear_site_status(contato.get("tem_site")),
        "tags_extra": tags_extra,
        "observacoes": "\n".join(partes_observacoes) or None,
    }


def _atualizar_lead_existente(conexao, existente, nome, campos, agora):
    """Preenche só o que está faltando no lead que já existe - nunca sobrescreve
    um campo que o usuário (ou uma busca anterior) já preencheu."""

    def preencher(atual, novo):
        vazio = atual is None or str(atual).strip() == ""
        return novo if vazio and novo else None

    candidatos = {
        "nome": preencher(existente.get("nome"), nome),
        "whatsapp_link": preencher(existente.get("whatsapp_link"), campos["whatsapp_link"]),
        "nicho": preencher(existente.get("nicho"), campos["nicho"]),
        "cidade": preencher(existente.get("cidade"), campos["cidade"]),
        "site_status": preencher(existente.get("site_status"), campos["site_status"]),
        "observacoes": preencher(existente.get("observacoes"), campos["observacoes"]),
    }
    if not (existente.get("origem") or "").strip():
        candidatos["origem"] = "kaptar"

    if campos["tags_extra"]:
        tags_atuais = existente.get("tags") or ""
        lista = [t.strip() for t in tags_atuais.split(",") if t.strip()]
        for tag in campos["tags_extra"]:
            if tag not in lista:
                lista.append(tag)
        novas_tags = ", ".join(lista)
        if novas_tags != tags_atuais:
            candidatos["tags"] = novas_tags

    sets = [f"{campo} = ?" for campo, valor in candidatos.items() if valor is not None]
    valores = [valor for valor in candidatos.values() if valor is not None]
    if not sets:
        return False

    sets.append("atualizado_em = ?")
    valores.append(agora)
    valores.append(existente["place_id"])
    conexao.execute(f"UPDATE leads SET {', '.join(sets)} WHERE place_id = ?", valores)
    return True


def importar_leads_csv(conexao, conteudo, nicho_padrao=None, cidade_padrao=None):
    """Importa o CSV do Kaptar (ou a lista simples "Nome, telefone") pra tabela
    `leads`. Lead com telefone que já existe no banco é atualizado em vez de
    duplicado; lead novo entra com place_id sintético `kaptar:<telefone>`
    (nunca colide com um place_id real do Google Maps). `nicho_padrao` e
    `cidade_padrao` só valem quando a linha não trouxer a própria coluna.

    Retorna {"importados": int, "atualizados": int, "descartados": {motivo: int}}."""
    preparar(conexao)

    contatos, invalidos = ler_contatos(conteudo)
    descartados = Counter(item["motivo"] for item in invalidos)

    importados = 0
    atualizados = 0
    agora = datetime.now().isoformat(timespec="seconds")
    hoje = datetime.now().date().isoformat()
    nicho_padrao = (nicho_padrao or "").strip() or None
    cidade_padrao = (cidade_padrao or "").strip() or None

    for contato in contatos:
        campos = _preparar_campos(contato)
        nome = contato["nome"] or "(sem nome)"
        nicho = campos["nicho"] or nicho_padrao
        cidade = campos["cidade"] or cidade_padrao
        campos["nicho"], campos["cidade"] = nicho, cidade

        existente = _achar_lead_por_telefone(conexao, campos["telefone"])
        if existente:
            _atualizar_lead_existente(conexao, existente, nome, campos, agora)
            atualizados += 1
            continue

        place_id = f"kaptar:{campos['telefone']}"
        tags = ", ".join(campos["tags_extra"]) or None
        conexao.execute(
            """
            INSERT INTO leads (
                place_id, nome, telefone, whatsapp_link, nicho, cidade,
                site_status, observacoes, tags, status, origem, visto_em, atualizado_em
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'novo', 'kaptar', ?, ?)
            ON CONFLICT(place_id) DO NOTHING
            """,
            (
                place_id, nome, campos["telefone"], campos["whatsapp_link"], nicho, cidade,
                campos["site_status"], campos["observacoes"], tags, hoje, agora,
            ),
        )
        importados += 1

    conexao.commit()
    return {"importados": importados, "atualizados": atualizados, "descartados": dict(descartados)}
