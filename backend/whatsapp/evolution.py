"""Cliente HTTP da Evolution API (a ponte com o WhatsApp).

Config: URL e nome da instância vêm de `EVOLUTION_URL`/`EVOLUTION_INSTANCIA` no
`backend/.env` (padrão `http://localhost:8080` e `prospector`). A chave da API
(`AUTHENTICATION_API_KEY`) NUNCA é copiada pra cá: é lida em tempo real de
`whatsapp/.env`, o mesmo arquivo que a Evolution usa - trocou a chave lá, o
backend já enxerga na próxima chamada.
"""

import logging
import os
import re

import requests
from dotenv import dotenv_values

import paths

logger = logging.getLogger(__name__)

# whatsapp/.env: pasta irmã de backend/, na raiz do projeto
CAMINHO_ENV_WHATSAPP = paths.DIR_RECURSOS.parent / "whatsapp" / ".env"

TIMEOUT_PADRAO_S = 15
TIMEOUT_ENVIO_S = 30


class ErroEvolution(Exception):
    """Erro ao falar com a Evolution API - mensagem já em português, pronta
    pra virar `{"erro": ...}` na resposta HTTP. `status` é o código HTTP
    devolvido pela Evolution (None quando a falha foi de conexão/timeout)."""

    def __init__(self, mensagem, status=None):
        super().__init__(mensagem)
        self.status = status


def _chave_api():
    valores = dotenv_values(CAMINHO_ENV_WHATSAPP)
    return (valores.get("AUTHENTICATION_API_KEY") or "").strip()


def _config():
    return {
        "url": (os.environ.get("EVOLUTION_URL") or "http://localhost:8080").rstrip("/"),
        "instancia": os.environ.get("EVOLUTION_INSTANCIA") or "prospector",
        "api_key": _chave_api(),
    }


def _request(metodo, rota, corpo=None, timeout=TIMEOUT_PADRAO_S):
    cfg = _config()
    url = cfg["url"] + rota
    try:
        resposta = requests.request(
            metodo,
            url,
            json=corpo,
            headers={"apikey": cfg["api_key"], "Content-Type": "application/json"},
            timeout=timeout,
        )
    except requests.exceptions.RequestException:
        logger.exception("falha ao falar com a Evolution API (%s %s)", metodo, rota)
        raise ErroEvolution(
            "Não foi possível falar com a Evolution API. Confira se o Docker está aberto "
            "e rode 'docker compose up -d' na pasta whatsapp."
        )

    try:
        dados = resposta.json() if resposta.text else None
    except ValueError:
        dados = resposta.text

    if not resposta.ok:
        mensagem = None
        if isinstance(dados, dict):
            resposta_aninhada = dados.get("response")
            if isinstance(resposta_aninhada, dict):
                mensagem = resposta_aninhada.get("message")
            mensagem = mensagem or dados.get("message")
            if isinstance(mensagem, list):
                mensagem = "; ".join(str(m) for m in mensagem)
        raise ErroEvolution(mensagem or f"Evolution respondeu {resposta.status_code}", status=resposta.status_code)

    return dados


def _estado_instancia(cfg):
    """→ {"existe": bool, "estado": "open"|"connecting"|"close"}."""
    try:
        resposta = _request("GET", f"/instance/connectionState/{cfg['instancia']}")
    except ErroEvolution as erro:
        if erro.status == 404:
            return {"existe": False, "estado": "close"}
        raise
    estado_txt = ((resposta or {}).get("instance") or {}).get("state") or "close"
    return {"existe": True, "estado": estado_txt}


def _numero_conectado(cfg):
    """Best-effort: o número do WhatsApp conectado, se a Evolution expuser
    (via /instance/fetchInstances). Não é essencial - se falhar, `numero`
    simplesmente vem None e a tela mostra só o estado."""
    try:
        resposta = _request("GET", "/instance/fetchInstances", timeout=8)
    except ErroEvolution:
        return None
    if not isinstance(resposta, list):
        return None
    for item in resposta:
        instancia = item.get("instance") if isinstance(item.get("instance"), dict) else item
        nome = instancia.get("instanceName") or instancia.get("name")
        if nome != cfg["instancia"]:
            continue
        bruto = instancia.get("owner") or instancia.get("ownerJid") or instancia.get("number") or ""
        digitos = re.sub(r"\D", "", str(bruto).split("@")[0])
        return digitos or None
    return None


def estado():
    """Estado atual da instância. Nunca lança: qualquer falha de conexão ou
    API vira `estado: "indisponivel"`, não uma exceção pra rota tratar."""
    cfg = _config()
    if not cfg["api_key"]:
        return {"evolution_ok": False, "conectado": False, "estado": "indisponivel",
                 "numero": None, "instancia": cfg["instancia"]}

    try:
        info = _estado_instancia(cfg)
    except ErroEvolution:
        return {"evolution_ok": False, "conectado": False, "estado": "indisponivel",
                 "numero": None, "instancia": cfg["instancia"]}

    estado_txt = info["estado"] if info["existe"] else "close"
    conectado = estado_txt == "open"
    numero = _numero_conectado(cfg) if conectado else None
    oficial = e_numero_oficial(numero)
    return {"evolution_ok": True, "conectado": conectado, "estado": estado_txt,
             "numero": numero, "instancia": cfg["instancia"],
             # campanha bloqueada só quando é o oficial E ninguém liberou de propósito
             "numero_oficial": oficial and not campanha_no_oficial_liberada(),
             "oficial_liberado": oficial and campanha_no_oficial_liberada()}


def campanha_no_oficial_liberada():
    """Exceção consciente: quem ainda não tem um chip separado pode liberar a
    campanha no número oficial, com teto diário baixo (ver
    aquecimento.TETO_NUMERO_OFICIAL). Tire a linha do .env ao trocar de chip."""
    return (os.environ.get("PERMITIR_CAMPANHA_NO_OFICIAL") or "").strip().lower() == "true"


# Número oficial do negócio (NUMERO_OFICIAL no backend/.env): nunca faz disparo
# em massa. Se ele cair por denúncia, cai junto o canal com os clientes.
# Campanha só roda em chip separado. Sem a variável, a trava fica desligada.
def _chave_numero(numero):
    """DDD + últimos 8 dígitos: ignora o 55 e o nono dígito, que o WhatsApp às
    vezes omite, pra "41 99999-0000" e "554199990000" serem o mesmo número."""
    digitos = re.sub(r"\D", "", str(numero or ""))
    if digitos.startswith("55") and len(digitos) >= 12:
        digitos = digitos[2:]
    return digitos[:2] + digitos[-8:] if len(digitos) >= 10 else ""


def e_numero_oficial(numero):
    oficial = _chave_numero(os.environ.get("NUMERO_OFICIAL"))
    conectado = _chave_numero(numero)
    return bool(oficial and conectado and oficial == conectado)


def _normalizar_qr(bruto):
    if not bruto:
        return None
    return bruto if bruto.startswith("data:") else f"data:image/png;base64,{bruto}"


def conectar():
    """Garante a instância (cria se não existir) e pede o QR code de conexão.
    → {"estado": "open"|"connecting", "qr_base64": str|None}. `qr_base64` vem
    None quando já está conectado."""
    cfg = _config()
    info = _estado_instancia(cfg)
    if not info["existe"]:
        _request(
            "POST", "/instance/create",
            corpo={"instanceName": cfg["instancia"], "qrcode": True, "integration": "WHATSAPP-BAILEYS"},
        )
        info = {"existe": True, "estado": "connecting"}

    if info["estado"] == "open":
        return {"estado": "open", "qr_base64": None}

    resposta = _request("GET", f"/instance/connect/{cfg['instancia']}")
    qr = _normalizar_qr((resposta or {}).get("base64")) if isinstance(resposta, dict) else None
    return {"estado": "connecting", "qr_base64": qr}


def desconectar():
    cfg = _config()
    _request("DELETE", f"/instance/logout/{cfg['instancia']}")


def numeros_com_whatsapp(numeros):
    """→ {digitos_do_numero: {"existe": bool, "jid": str|None}}."""
    cfg = _config()
    resposta = _request("POST", f"/chat/whatsappNumbers/{cfg['instancia']}", corpo={"numbers": list(numeros)})
    mapa = {}
    for item in resposta if isinstance(resposta, list) else []:
        chave = re.sub(r"\D", "", str(item.get("number") or ""))
        if chave:
            mapa[chave] = {"existe": bool(item.get("exists")), "jid": item.get("jid")}
    return mapa


def enviar_texto(numero, texto):
    """Envia uma mensagem de texto. → resposta crua da Evolution (tem
    `key.id`, usado como id_externo pra dedup com o webhook). Lança
    ErroEvolution em qualquer falha."""
    cfg = _config()
    return _request(
        "POST", f"/message/sendText/{cfg['instancia']}",
        corpo={"number": numero, "text": texto, "delay": 1200, "linkPreview": False},
        timeout=TIMEOUT_ENVIO_S,
    )
