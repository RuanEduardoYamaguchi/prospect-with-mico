"""Rotas da análise de oportunidade (micro-demos). Contrato em INTEGRACAO.md."""

from flask import Blueprint, jsonify, request

import ia
from microdemo import analise

bp = Blueprint("microdemo", __name__)


@bp.route("/api/leads/<place_id>/oportunidade")
def obter_oportunidade(place_id):
    lead = analise.carregar_lead(place_id)
    if lead is None:
        return jsonify({"erro": "Lead não encontrado."}), 404
    return jsonify({
        "analise": analise.ultima_analise(place_id),
        "score": analise.calcular_score_do_lead(lead),
        "score_min": analise.score_minimo(),
    })


@bp.route("/api/leads/<place_id>/oportunidade/analisar", methods=["POST"])
def analisar_oportunidade(place_id):
    try:
        resultado = analise.analisar(place_id)
    except LookupError:
        return jsonify({"erro": "Lead não encontrado."}), 404
    except analise.ScoreAbaixoDoMinimo as erro:
        return jsonify({
            "erro": f"o score deste lead ({erro.score}) está abaixo do mínimo para análise ({erro.minimo})"
        }), 400
    except ia.NenhumProvedorDisponivel as erro:
        detalhe = ia.traduzir_erro_ia(erro.erro_final) if erro.erro_final else "nenhuma chave de IA configurada"
        return jsonify({"erro": f"Não consegui analisar agora: {detalhe}"}), 500
    return jsonify({"analise": resultado})


@bp.route("/api/configuracoes/analise-oportunidade", methods=["GET", "POST"])
def configuracao_analise_oportunidade():
    if request.method == "POST":
        corpo = request.get_json(silent=True) or {}
        try:
            analise.salvar_score_minimo(corpo.get("score_min"))
        except ValueError as erro:
            return jsonify({"erro": str(erro)}), 400
    return jsonify({"score_min": analise.score_minimo()})
