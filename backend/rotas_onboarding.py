"""Checklist de primeiros passos: o que já está configurado e o que falta.

A tela inicial usa isso pra guiar quem acabou de instalar. Só lê estado local
(cofre de credenciais, banco e arquivos): não chama nenhuma API externa.
"""

from flask import Blueprint, jsonify

import db
import ia
from constantes import MARCADOR_PREENCHER

bp = Blueprint("onboarding", __name__)

PROVEDORES_IA = ("anthropic", "gemini", "groq", "nvidia")


def _estrategia_personalizada():
    """Escrita por quem usa e sem sobra do modelo ([PREENCHER...])."""
    texto = ia.ler_estrategia_abordagem()
    return bool(texto) and MARCADOR_PREENCHER not in texto


@bp.route("/api/onboarding")
def checklist_primeiros_passos():
    conexao = db.conectar()
    try:
        total_leads = conexao.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        leads_contatados = conexao.execute(
            "SELECT COUNT(*) FROM leads WHERE status != 'novo'"
        ).fetchone()[0]
    finally:
        conexao.close()

    return jsonify({
        "ia_configurada": any(db.obter_config(provedor) for provedor in PROVEDORES_IA),
        "places_configurada": bool(db.obter_config("places")),
        "perfil_preenchido": bool((db.obter_config("vendedor_nome") or "").strip()),
        "estrategia_personalizada": _estrategia_personalizada(),
        "total_leads": total_leads,
        "leads_contatados": leads_contatados,
    })
