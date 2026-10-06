"""Rotas do WhatsApp: conexão com a Evolution API, envio manual, aquecimento
do chip e campanhas de prospecção. Contrato completo em
`docs/INTEGRACAO.md` - mudou aqui, muda lá também.
"""

import logging
import threading

from flask import Blueprint, jsonify, request

import db
import rotas_conversa
from whatsapp import aquecimento, autoresponder, campanha, evolution, webhook
from whatsapp import texto as wa_texto

logger = logging.getLogger(__name__)

bp = Blueprint("whatsapp", __name__)

ERRO_NUMERO_OFICIAL = (
    "o WhatsApp conectado é o seu número oficial (NUMERO_OFICIAL no backend/.env). "
    "Campanha só roda em chip separado: desconecte e leia o QR code com outro chip."
)


def _status_http_da_falha(erro):
    return erro.status if erro.status and erro.status < 500 else 502


# ---------------------------------------------------------------------------
# Conexão
# ---------------------------------------------------------------------------

@bp.route("/api/whatsapp/estado")
def estado_whatsapp():
    return jsonify(evolution.estado())


@bp.route("/api/whatsapp/conectar", methods=["POST"])
def conectar_whatsapp():
    try:
        return jsonify(evolution.conectar())
    except evolution.ErroEvolution as erro:
        return jsonify({"erro": str(erro)}), _status_http_da_falha(erro)


@bp.route("/api/whatsapp/desconectar", methods=["POST"])
def desconectar_whatsapp():
    try:
        evolution.desconectar()
    except evolution.ErroEvolution as erro:
        return jsonify({"erro": str(erro)}), _status_http_da_falha(erro)
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Resposta automática por IA (interruptor geral)
# ---------------------------------------------------------------------------

@bp.route("/api/whatsapp/autoresposta")
def autoresposta_whatsapp():
    return jsonify({"ativa": autoresponder.autoresposta_ativa()})


@bp.route("/api/whatsapp/autoresposta", methods=["POST"])
def definir_autoresposta_whatsapp():
    ativa = (request.json or {}).get("ativa")
    if not isinstance(ativa, bool):
        return jsonify({"erro": "informe ativa como true ou false"}), 400
    db.salvar_config(autoresponder.CONFIG_AUTORESPOSTA, "1" if ativa else "0")
    return jsonify({"ativa": ativa})


# ---------------------------------------------------------------------------
# Aquecimento
# ---------------------------------------------------------------------------

@bp.route("/api/whatsapp/aquecimento")
def aquecimento_whatsapp():
    return jsonify(aquecimento.resumo())


# ---------------------------------------------------------------------------
# Envio manual
# ---------------------------------------------------------------------------

@bp.route("/api/whatsapp/enviar", methods=["POST"])
def enviar_whatsapp():
    corpo = request.json or {}
    place_id = str(corpo.get("place_id") or "").strip()
    texto_bruto = str(corpo.get("texto") or "").strip()

    if not place_id:
        return jsonify({"erro": "informe o lead (place_id)"}), 400
    if not texto_bruto:
        return jsonify({"erro": "escreva o texto antes de enviar"}), 400

    conexao = db.conectar()
    try:
        lead = conexao.execute("SELECT * FROM leads WHERE place_id = ?", (place_id,)).fetchone()
    finally:
        conexao.close()
    if not lead:
        return jsonify({"erro": "lead não encontrado"}), 404
    lead = dict(lead)

    if lead.get("wa_optout"):
        return jsonify({"erro": "este lead pediu pra não receber mais mensagens"}), 400

    canonico = rotas_conversa.normalizar_telefone(lead.get("telefone"))
    if not canonico:
        return jsonify({"erro": "lead sem telefone válido"}), 400
    numero_evolution = "55" + canonico

    # follow-up é justamente mandar de novo pra quem já recebeu; primeiro
    # contato repetido continua bloqueado
    followup = bool(corpo.get("followup"))
    if not followup and campanha.telefone_ja_recebeu(numero_evolution):
        return jsonify({
            "erro": "este número já recebeu mensagem antes. Se for um retorno, envie como follow-up."
        }), 400

    # responder quem já respondeu é conversa, não prospecção fria: o teto do
    # aquecimento não pode travar a resposta pra um lead quente
    em_conversa = followup and lead.get("status") in ("respondeu", "fechou")
    resumo_aquecimento = aquecimento.resumo()
    if not em_conversa and resumo_aquecimento["restantes_hoje"] <= 0:
        return jsonify({
            "erro": f"o teto de envios de hoje já foi atingido ({resumo_aquecimento['teto_hoje']} mensagens)"
        }), 400

    estado = evolution.estado()
    if not estado.get("conectado"):
        return jsonify({"erro": "o WhatsApp não está conectado. Leia o QR code antes de enviar."}), 400

    texto_final = wa_texto.montar_mensagem(texto_bruto, lead)

    try:
        resposta = evolution.enviar_texto(numero_evolution, texto_final)
    except evolution.ErroEvolution as erro:
        campanha.registrar_envio_manual(place_id, numero_evolution, texto_final, "falhou", erro=str(erro))
        return jsonify({"erro": str(erro)}), _status_http_da_falha(erro)

    id_externo = (resposta.get("key") or {}).get("id") if isinstance(resposta, dict) else None
    envio = campanha.registrar_envio_manual(place_id, numero_evolution, texto_final, "enviado", id_externo=id_externo)
    return jsonify({"ok": True, "envio": envio})


@bp.route("/api/whatsapp/enviar-numero", methods=["POST"])
def enviar_numero_whatsapp():
    """Envio avulso pra um número que não precisa estar cadastrado como lead -
    teste, contato pessoal, qualquer conversa fora do funil de prospecção. Não
    passa pelas travas de campanha (optout, já recebeu antes, teto do
    aquecimento): quem manda aqui já escolheu o número na mão."""
    corpo = request.json or {}
    telefone_bruto = str(corpo.get("telefone") or "").strip()
    texto_bruto = str(corpo.get("texto") or "").strip()

    if not texto_bruto:
        return jsonify({"erro": "escreva o texto antes de enviar"}), 400

    canonico = rotas_conversa.normalizar_telefone(telefone_bruto)
    if not canonico or len(canonico) not in (10, 11):
        return jsonify({"erro": "informe um número válido, com DDD (ex: 65999998888)"}), 400

    estado = evolution.estado()
    if not estado.get("conectado"):
        return jsonify({"erro": "o WhatsApp não está conectado. Leia o QR code antes de enviar."}), 400

    numero_evolution = "55" + canonico
    try:
        resposta = evolution.enviar_texto(numero_evolution, texto_bruto)
    except evolution.ErroEvolution as erro:
        return jsonify({"erro": str(erro)}), _status_http_da_falha(erro)

    # se o número bater com um lead do Maps já cadastrado, registra no cockpit
    # dele normalmente - assim a conversa não fica invisível pro sistema
    canal, lead_ref = rotas_conversa._resolver_lead_por_telefone(telefone_bruto)
    if canal == "maps" and lead_ref:
        id_externo = (resposta.get("key") or {}).get("id") if isinstance(resposta, dict) else None
        campanha.registrar_envio_manual(lead_ref, numero_evolution, texto_bruto, "enviado", id_externo=id_externo)

    return jsonify({"ok": True, "numero": numero_evolution})


# ---------------------------------------------------------------------------
# Webhook (Evolution -> app)
# ---------------------------------------------------------------------------

@bp.route("/api/whatsapp/webhook", methods=["POST"])
def webhook_whatsapp():
    # a Evolution sempre manda JSON, mas a rota tem que responder 200 mesmo
    # pra um corpo vazio/malformado - por isso get_json(silent=True) em vez de
    # request.json (que devolveria 415/400 antes até de chegar no try/except).
    # Processa numa thread separada: a resposta automática chama IA (até 45s)
    # e a Evolution (até 30s), e a Evolution reenvia o evento se o ACK demorar.
    payload = request.get_json(silent=True) or {}
    threading.Thread(target=webhook.processar_evento, args=(payload,), daemon=True).start()
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Campanhas
# ---------------------------------------------------------------------------

@bp.route("/api/campanhas/previa", methods=["POST"])
def previa_campanha():
    corpo = request.json or {}
    filtros = corpo.get("filtros") or {}
    template = str(corpo.get("template") or "")
    limite = corpo.get("limite")

    if not template.strip():
        return jsonify({"erro": "escreva o template da mensagem"}), 400

    return jsonify(campanha.previa(filtros, template, limite))


@bp.route("/api/campanhas", methods=["POST"])
def criar_campanha_whatsapp():
    corpo = request.json or {}
    nome = corpo.get("nome")
    filtros = corpo.get("filtros") or {}
    template = str(corpo.get("template") or "")
    limite = corpo.get("limite")
    ritmo = corpo.get("ritmo") or {}
    checar_whatsapp = corpo.get("checar_whatsapp", True)

    if not template.strip():
        return jsonify({"erro": "escreva o template da mensagem"}), 400
    if wa_texto.contem_link(template):
        return jsonify({
            "erro": "o primeiro contato automático não pode ter link - é o que mais gera denúncia"
        }), 400
    if wa_texto.contem_marcador_preencher(template):
        return jsonify({
            "erro": "o template ainda tem trechos [PREENCHER: ...]. Troque pelo seu nome e o da sua empresa."
        }), 400
    if campanha.existe_campanha_ativa():
        return jsonify({
            "erro": "já existe uma campanha rodando, pausada ou interrompida. Resolva ela antes de criar outra."
        }), 400

    estado = evolution.estado()
    if not estado.get("conectado"):
        return jsonify({"erro": "o WhatsApp não está conectado. Leia o QR code antes de criar a campanha."}), 400
    if estado.get("numero_oficial"):
        return jsonify({"erro": ERRO_NUMERO_OFICIAL}), 400

    previa_resultado = campanha.previa(filtros, template, limite)
    if not previa_resultado["leads"]:
        return jsonify({"erro": "nenhum lead sobrou depois dos filtros"}), 400

    nova = campanha.criar_campanha(nome, filtros, template, limite, ritmo, checar_whatsapp)
    return jsonify({"campanha": nova})


@bp.route("/api/campanhas")
def listar_campanhas_whatsapp():
    return jsonify(campanha.listar())


@bp.route("/api/campanhas/<int:campanha_id>/parar", methods=["POST"])
def parar_campanha_whatsapp(campanha_id):
    resultado, erro = campanha.parar(campanha_id)
    if erro:
        status = 404 if "não encontrada" in erro else 400
        return jsonify({"erro": erro}), status
    return jsonify({"campanha": resultado})


@bp.route("/api/campanhas/<int:campanha_id>/retomar", methods=["POST"])
def retomar_campanha_whatsapp(campanha_id):
    estado = evolution.estado()
    if not estado.get("conectado"):
        return jsonify({"erro": "o WhatsApp não está conectado. Leia o QR code antes de retomar."}), 400
    if estado.get("numero_oficial"):
        return jsonify({"erro": ERRO_NUMERO_OFICIAL}), 400

    resultado, erro = campanha.retomar(campanha_id)
    if erro:
        status = 404 if "não encontrada" in erro else 400
        return jsonify({"erro": erro}), status
    return jsonify({"campanha": resultado})


@bp.route("/api/campanhas/<int:campanha_id>/descartar", methods=["POST"])
def descartar_campanha_whatsapp(campanha_id):
    resultado, erro = campanha.descartar(campanha_id)
    if erro:
        return jsonify({"erro": erro}), 404
    return jsonify({"campanha": resultado})
