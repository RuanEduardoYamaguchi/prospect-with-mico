"""Resposta automática por IA ao lead que respondeu no WhatsApp (canal `maps`).

A IA conduz a conversa sozinha reaproveitando o mesmo analista de negociação
do cockpit manual (`ia.analisar_conversa_com_fallback`) até a leitura dela
chegar em `negociacao` ou `fechamento` - a partir daí ela para de vez
(`leads.wa_ia_pausada`, permanente) e avisa o responsável pelo próprio
WhatsApp conectado, pra ele assumir a conversa manualmente. Nunca lança:
é chamada a partir do webhook, que sempre tem que responder 200 pra Evolution.
"""

import logging
import os

import db
import ia
import rotas_conversa

from . import campanha, evolution

logger = logging.getLogger(__name__)

ESTAGIOS_QUE_QUALIFICAM = {"negociacao", "fechamento"}

# Sem número padrão: quem quer o aviso de lead quente define
# NUMERO_NOTIFICACAO_QUALIFICACAO no backend/.env (DDD + número, sem o 55).
NUMERO_NOTIFICACAO_PADRAO = ""


CONFIG_AUTORESPOSTA = "wa_autoresposta_ativa"


def autoresposta_ativa():
    """Interruptor geral da resposta automática. Padrão: desligada (só liga
    se alguém ligar no painel)."""
    return str(db.obter_config(CONFIG_AUTORESPOSTA, "0")).strip() == "1"


def _numero_notificacao():
    bruto = os.environ.get("NUMERO_NOTIFICACAO_QUALIFICACAO") or NUMERO_NOTIFICACAO_PADRAO
    canonico = rotas_conversa.normalizar_telefone(bruto)
    return "55" + canonico if canonico else None


def _buscar_lead(place_id):
    conexao = db.conectar()
    try:
        linha = conexao.execute("SELECT * FROM leads WHERE place_id = ?", (place_id,)).fetchone()
    finally:
        conexao.close()
    return dict(linha) if linha else None


def _marcar_ia_pausada(place_id):
    conexao = db.conectar()
    try:
        conexao.execute("UPDATE leads SET wa_ia_pausada = 1 WHERE place_id = ?", (place_id,))
        conexao.commit()
    finally:
        conexao.close()


def _notificar_responsavel(lead, analise, ultima_mensagem_lead):
    numero = _numero_notificacao()
    if not numero:
        logger.warning(
            "lead %s qualificado, mas não há número de notificação válido "
            "(defina NUMERO_NOTIFICACAO_QUALIFICACAO no backend/.env)", lead.get("place_id")
        )
        return

    texto_aviso = (
        f"lead quente: {lead.get('nome')} ({lead.get('cidade') or 'cidade não informada'})\n"
        f"tel: {lead.get('telefone')}\n\n"
        f"{analise.get('leitura') or ''}\n\n"
        f'última msg do lead: "{ultima_mensagem_lead}"'
    ).strip()

    try:
        evolution.enviar_texto(numero, texto_aviso)
    except evolution.ErroEvolution:
        logger.exception(
            "falha ao notificar responsável sobre lead qualificado %s", lead.get("place_id")
        )


def _responder_automaticamente(place_id, telefone_lead, resposta):
    # a análise da IA demora: se desligaram nesse meio tempo, não envia
    if not autoresposta_ativa():
        logger.info("autoresponder: desligada durante a análise, não envio ao lead %s", place_id)
        return

    canonico = rotas_conversa.normalizar_telefone(telefone_lead)
    if not canonico:
        return
    numero_evolution = "55" + canonico

    try:
        resultado = evolution.enviar_texto(numero_evolution, resposta)
    except evolution.ErroEvolution as erro:
        campanha.registrar_envio_manual(place_id, numero_evolution, resposta, "falhou", erro=str(erro))
        return

    id_externo = (resultado.get("key") or {}).get("id") if isinstance(resultado, dict) else None
    campanha.registrar_envio_manual(place_id, numero_evolution, resposta, "enviado", id_externo=id_externo)


def processar_mensagem_recebida(place_id, telefone_lead):
    """Chamado pelo webhook depois de gravar uma mensagem NOVA do lead (canal
    `maps`). Decide se a IA responde sozinha ou se o lead já qualificou e é
    hora de chamar o responsável."""
    try:
        if not autoresposta_ativa():
            logger.info("autoresponder: resposta automática desligada, não respondo o lead %s", place_id)
            return

        lead = _buscar_lead(place_id)
        if not lead or lead.get("wa_ia_pausada") or lead.get("wa_optout"):
            return

        if not evolution.estado().get("conectado"):
            logger.info("autoresponder: WhatsApp desconectado, não respondo o lead %s", place_id)
            return

        conexao = db.conectar()
        try:
            mensagens = rotas_conversa._listar_mensagens(conexao, "maps", place_id)
        finally:
            conexao.close()

        analise, _provedor, _avisos = ia.analisar_conversa_com_fallback(lead, mensagens)

        if analise["estagio"] in ESTAGIOS_QUE_QUALIFICAM:
            _marcar_ia_pausada(place_id)
            ultima_do_lead = next(
                (m["texto"] for m in reversed(mensagens) if m["autor"] == "lead"), ""
            )
            _notificar_responsavel(lead, analise, ultima_do_lead)
            return

        resposta = analise.get("resposta_sugerida")
        if resposta:
            _responder_automaticamente(place_id, telefone_lead, resposta)
    except ia.NenhumProvedorDisponivel:
        logger.warning("autoresponder: nenhum provedor de IA disponível para o lead %s", place_id)
    except evolution.ErroEvolution:
        logger.exception("autoresponder: falha ao falar com a Evolution para o lead %s", place_id)
    except Exception:
        logger.exception("autoresponder: falha inesperada ao processar o lead %s", place_id)
