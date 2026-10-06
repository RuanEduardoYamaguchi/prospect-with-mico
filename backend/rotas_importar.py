"""Rotas de importação de dados externos: CSV de prospecção (Kaptar ou lista
simples "Nome, telefone"). Ver docs/INTEGRACAO.md, seção "Importação"."""

import logging

from flask import Blueprint, jsonify, request

import db
import importar_kaptar

logger = logging.getLogger(__name__)

bp = Blueprint("importar", __name__)

# ~5 MB de texto: generoso até pro maior export que o Kaptar costuma gerar,
# sem deixar o endpoint aceitar um payload gigante por engano.
MAX_CARACTERES_CONTEUDO_CSV = 5_000_000


@bp.route("/api/importar/kaptar", methods=["POST"])
def importar_kaptar_rota():
    corpo = request.json or {}
    conteudo = corpo.get("conteudo")
    if not isinstance(conteudo, str) or not conteudo.strip():
        return jsonify({"erro": "informe o conteúdo do CSV"}), 400
    if len(conteudo) > MAX_CARACTERES_CONTEUDO_CSV:
        return jsonify({"erro": "CSV grande demais"}), 400

    nicho_padrao = corpo.get("nicho_padrao")
    cidade_padrao = corpo.get("cidade_padrao")

    conexao = db.conectar()
    try:
        resultado = importar_kaptar.importar_leads_csv(
            conexao, conteudo,
            nicho_padrao=str(nicho_padrao) if nicho_padrao else None,
            cidade_padrao=str(cidade_padrao) if cidade_padrao else None,
        )
    except Exception:
        logger.exception("falha ao importar CSV do Kaptar")
        return jsonify({"erro": "não foi possível importar o CSV. Confira o formato e tente de novo."}), 500
    finally:
        conexao.close()

    return jsonify(resultado)
