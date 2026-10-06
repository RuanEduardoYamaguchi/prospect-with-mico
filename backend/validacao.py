"""Validações compartilhadas entre as rotas."""

from flask import jsonify

from constantes import MAX_IDS_BULK


def validar_ids_bulk(ids, nome_campo):
    """Valida a lista de ids de uma ação em lote. Retorna (ids, None) quando ok,
    ou (None, resposta_de_erro) quando vazia ou acima do limite - evita estourar
    o limite de variáveis vinculadas do SQLite num IN (...)."""
    ids = ids or []
    if not ids:
        return None, (jsonify({"erro": f"informe ao menos um {nome_campo}"}), 400)
    if len(ids) > MAX_IDS_BULK:
        return None, (jsonify({
            "erro": f"no máximo {MAX_IDS_BULK} itens por ação em lote (você enviou {len(ids)})"
        }), 400)
    return ids, None
