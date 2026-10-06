"""Aquecimento do chip: teto de envios por dia, crescente, pra não queimar um
número novo (ver `whatsapp/README.md`, seção "Cuidado com o
número"). Teto: 15 no dia 1, +5 por dia sem falha grave, até 150. Um dia com 5+
falhas não sobe o teto do dia seguinte. O dia 1 é o dia do PRIMEIRO envio já
registrado (nunca da instalação do app) - guardado em `configuracoes` sob a
chave `wa_aquecimento_inicio`.
"""

import os
from datetime import date, timedelta

import db
from whatsapp import evolution

CHAVE_CONFIG_INICIO = "wa_aquecimento_inicio"

# Teto diário enquanto a campanha estiver liberada no número oficial
# (PERMITIR_CAMPANHA_NO_OFICIAL=true no backend/.env). Sobrescrevível por
# TETO_NUMERO_OFICIAL no .env; 0 tira esse teto e vale só o do aquecimento.
TETO_NUMERO_OFICIAL = 20


def _teto_numero_oficial():
    try:
        return int(os.environ.get("TETO_NUMERO_OFICIAL", TETO_NUMERO_OFICIAL))
    except ValueError:
        return TETO_NUMERO_OFICIAL

TETO_INICIAL = 15
INCREMENTO_DIARIO = 5
TETO_MAXIMO = 150
FALHAS_QUE_TRAVAM_O_TETO = 5


def _data_inicio():
    bruta = db.obter_config(CHAVE_CONFIG_INICIO)
    if not bruta:
        return None
    try:
        return date.fromisoformat(bruta)
    except ValueError:
        return None


def marcar_inicio_se_necessario():
    """Chamado no primeiro envio bem-sucedido (ou falho - já é uso do chip) de
    todos os tempos: fixa o dia 1 do aquecimento. Idempotente."""
    if _data_inicio() is None:
        db.salvar_config(CHAVE_CONFIG_INICIO, date.today().isoformat())


def dia_do_chip():
    """1 antes do primeiro envio (ainda não começou a contar)."""
    inicio = _data_inicio()
    if inicio is None:
        return 1
    return max(1, (date.today() - inicio).days + 1)


def _contar_por_dia(status, dia):
    conexao = db.conectar()
    try:
        linha = conexao.execute(
            "SELECT COUNT(*) FROM wa_envios WHERE status = ? AND substr(enviado_em, 1, 10) = ?",
            (status, dia.isoformat()),
        ).fetchone()
        return linha[0] or 0
    finally:
        conexao.close()


def teto_do_dia(dia):
    """Teto de envios do dia N do aquecimento (dia 1 = primeiro dia de uso).
    Sobe 5 a cada dia que passou SEM 5+ falhas, até o teto de 150."""
    inicio = _data_inicio()
    teto = TETO_INICIAL
    if inicio is None or dia <= 1:
        return teto
    for deslocamento in range(dia - 1):
        dia_passado = inicio + timedelta(days=deslocamento)
        if _contar_por_dia("falhou", dia_passado) < FALHAS_QUE_TRAVAM_O_TETO:
            teto = min(TETO_MAXIMO, teto + INCREMENTO_DIARIO)
    return teto


def resumo():
    """→ {dia_do_chip, teto_hoje, enviados_hoje, restantes_hoje, falhas_ontem}
    (forma exata do `GET /api/whatsapp/aquecimento`)."""
    dia = dia_do_chip()
    teto = teto_do_dia(dia)
    teto_oficial = _teto_numero_oficial()
    if teto_oficial > 0 and evolution.campanha_no_oficial_liberada():
        # disparando pelo número oficial: teto fixo baixo, não importa o
        # aquecimento. Se ele cair, cai o canal com os clientes junto.
        teto = min(teto, teto_oficial)
    hoje = date.today()
    enviados_hoje = _contar_por_dia("enviado", hoje)
    falhas_ontem = _contar_por_dia("falhou", hoje - timedelta(days=1))
    return {
        "dia_do_chip": dia,
        "teto_hoje": teto,
        "enviados_hoje": enviados_hoje,
        "restantes_hoje": max(0, teto - enviados_hoje),
        "falhas_ontem": falhas_ontem,
    }


def restantes_hoje():
    return resumo()["restantes_hoje"]
