"""Rotas de métricas e analytics: dashboards do Maps, do Instagram e combinado,
funil de conversão, desempenho por nicho, meta semanal e follow-ups do dia."""

from datetime import date, datetime, timedelta

from flask import Blueprint, jsonify, request

import db
from constantes import ESTAGIOS_FUNIL

bp = Blueprint("analytics", __name__)


@bp.route("/api/metricas")
def metricas():
    """Contagens gerais pro dashboard: total de leads ativos, por status, taxa de conversão."""
    if not db.CAMINHO_BANCO.exists():
        return jsonify({"total": 0, "por_status": {}, "taxa_conversao": 0})

    conexao = db.conectar()
    try:
        total = conexao.execute("SELECT COUNT(*) c FROM leads WHERE status != 'ignorado'").fetchone()["c"]
        linhas_por_status = conexao.execute(
            "SELECT status, COUNT(*) c FROM leads WHERE status != 'ignorado' GROUP BY status"
        ).fetchall()
        lembretes_hoje = conexao.execute(
            "SELECT COUNT(*) c FROM leads WHERE status != 'ignorado' AND proximo_followup IS NOT NULL "
            "AND proximo_followup <= ?",
            (date.today().isoformat(),),
        ).fetchone()["c"]
    finally:
        conexao.close()

    por_status = {linha["status"]: linha["c"] for linha in linhas_por_status}
    fechados = por_status.get("fechou", 0)
    taxa_conversao = round(100 * fechados / total, 1) if total else 0

    return jsonify(
        {
            "total": total,
            "por_status": por_status,
            "taxa_conversao": taxa_conversao,
            "lembretes_hoje": lembretes_hoje,
        }
    )


def _contar_funil_por_tabela(conexao, tabela):
    """Quantos leads (ativos, isto é, não ignorados) já alcançaram cada estágio
    do funil. O funil é uma progressão linear (novo → contatado → respondeu →
    fechou): um lead cujo status atual é "respondeu" conta também em "novo" e
    "contatado", mesmo que tenha pulado direto pra lá sem passar pelo bulk-status
    intermediário. "recusou" não pertence ao funil (é uma saída, não avanço)."""
    status_por_lead = conexao.execute(
        f"SELECT status FROM {tabela} WHERE status != 'ignorado'"
    ).fetchall()

    contagem = {estagio: 0 for estagio in ESTAGIOS_FUNIL}
    for linha in status_por_lead:
        status_atual = linha["status"]
        if status_atual not in ESTAGIOS_FUNIL:
            continue  # "recusou": não avançou em nenhum estágio do funil
        indice_atual = ESTAGIOS_FUNIL.index(status_atual)
        for estagio in ESTAGIOS_FUNIL[: indice_atual + 1]:
            contagem[estagio] += 1

    return contagem


def _contar_por_nicho_tabela(conexao, tabela):
    """Total de leads e taxa de conversão (fechou/total) por nicho (já separado da
    cidade), considerando só leads ativos (não ignorados). Ordenado por total desc."""
    linhas = conexao.execute(
        f"""
        SELECT
            nicho,
            COUNT(*) AS total,
            SUM(CASE WHEN status = 'fechou' THEN 1 ELSE 0 END) AS fechados
        FROM {tabela}
        WHERE status != 'ignorado' AND nicho IS NOT NULL AND nicho != ''
        GROUP BY nicho
        ORDER BY total DESC
        """
    ).fetchall()

    nichos = {}
    for linha in linhas:
        nichos[linha["nicho"]] = {
            "total": linha["total"],
            "fechados": linha["fechados"] or 0,
        }
    return nichos


def _nichos_dict_para_lista(nichos):
    lista = []
    for nome, dados in nichos.items():
        total = dados["total"]
        fechados = dados["fechados"]
        taxa_conversao = round(100 * fechados / total, 1) if total else 0
        lista.append({
            "nicho": nome,
            "total": total,
            "fechados": fechados,
            "taxa_conversao": taxa_conversao,
        })
    lista.sort(key=lambda n: n["total"], reverse=True)
    return lista


@bp.route("/api/analytics/funil")
def analytics_funil():
    if not db.CAMINHO_BANCO.exists():
        return jsonify({"estagios": [{"status": s, "total": 0} for s in ESTAGIOS_FUNIL]})

    conexao = db.conectar()
    try:
        contagem = _contar_funil_por_tabela(conexao, "leads")
    finally:
        conexao.close()

    return jsonify({
        "estagios": [{"status": s, "total": contagem[s]} for s in ESTAGIOS_FUNIL],
    })


@bp.route("/api/analytics/por-nicho")
def analytics_por_nicho():
    if not db.CAMINHO_BANCO.exists():
        return jsonify({"nichos": []})

    conexao = db.conectar()
    try:
        nichos = _contar_por_nicho_tabela(conexao, "leads")
    finally:
        conexao.close()

    return jsonify({"nichos": _nichos_dict_para_lista(nichos)})


@bp.route("/api/analytics/funil-combinado")
def analytics_funil_combinado():
    conexao = db.conectar()
    try:
        contagem_maps = (
            _contar_funil_por_tabela(conexao, "leads") if db.CAMINHO_BANCO.exists() else {e: 0 for e in ESTAGIOS_FUNIL}
        )
        contagem_instagram = _contar_funil_por_tabela(conexao, "instagram_leads")
    finally:
        conexao.close()

    combinado = {
        estagio: contagem_maps[estagio] + contagem_instagram[estagio]
        for estagio in ESTAGIOS_FUNIL
    }
    return jsonify({
        "estagios": [{"status": s, "total": combinado[s]} for s in ESTAGIOS_FUNIL],
    })


@bp.route("/api/analytics/por-nicho-combinado")
def analytics_por_nicho_combinado():
    conexao = db.conectar()
    try:
        nichos_maps = _contar_por_nicho_tabela(conexao, "leads") if db.CAMINHO_BANCO.exists() else {}
        nichos_instagram = _contar_por_nicho_tabela(conexao, "instagram_leads")
    finally:
        conexao.close()

    combinado = dict(nichos_maps)
    for nome, dados in nichos_instagram.items():
        if nome in combinado:
            combinado[nome] = {
                "total": combinado[nome]["total"] + dados["total"],
                "fechados": combinado[nome]["fechados"] + dados["fechados"],
            }
        else:
            combinado[nome] = dados

    return jsonify({"nichos": _nichos_dict_para_lista(combinado)})


@bp.route("/api/instagram/metricas")
def metricas_instagram():
    """Contagens gerais dos leads do Instagram: total ativos, por status, taxa de conversão."""
    conexao = db.conectar()
    try:
        total = conexao.execute(
            "SELECT COUNT(*) c FROM instagram_leads WHERE status != 'ignorado'"
        ).fetchone()["c"]
        linhas_por_status = conexao.execute(
            "SELECT status, COUNT(*) c FROM instagram_leads WHERE status != 'ignorado' GROUP BY status"
        ).fetchall()
        lembretes_hoje = conexao.execute(
            "SELECT COUNT(*) c FROM instagram_leads WHERE status != 'ignorado' AND proximo_followup IS NOT NULL "
            "AND proximo_followup <= ?",
            (date.today().isoformat(),),
        ).fetchone()["c"]
    finally:
        conexao.close()

    por_status = {linha["status"]: linha["c"] for linha in linhas_por_status}
    fechados = por_status.get("fechou", 0)
    taxa_conversao = round(100 * fechados / total, 1) if total else 0

    return jsonify({
        "total": total,
        "por_status": por_status,
        "taxa_conversao": taxa_conversao,
        "lembretes_hoje": lembretes_hoje,
    })


@bp.route("/api/instagram/analytics/funil")
def analytics_funil_instagram():
    """Mesma lógica cumulativa de /api/analytics/funil, mas sobre instagram_leads."""
    conexao = db.conectar()
    try:
        contagem = _contar_funil_por_tabela(conexao, "instagram_leads")
    finally:
        conexao.close()

    return jsonify({
        "estagios": [{"status": s, "total": contagem[s]} for s in ESTAGIOS_FUNIL],
    })


@bp.route("/api/instagram/analytics/por-nicho")
def analytics_por_nicho_instagram():
    """Mesma lógica de /api/analytics/por-nicho, mas sobre instagram_leads."""
    conexao = db.conectar()
    try:
        nichos = _contar_por_nicho_tabela(conexao, "instagram_leads")
    finally:
        conexao.close()

    return jsonify({"nichos": _nichos_dict_para_lista(nichos)})


@bp.route("/api/metricas-combinadas")
def metricas_combinadas():
    """Soma as métricas dos dois canais (Maps + Instagram) - usado no dashboard
    unificado. Reaproveita as mesmas queries de /api/metricas e /api/instagram/metricas,
    só que somando os totais em vez de devolver dois blocos separados."""
    conexao = db.conectar()
    try:
        total_maps = 0
        por_status_maps = {}
        if db.CAMINHO_BANCO.exists():
            total_maps = conexao.execute(
                "SELECT COUNT(*) c FROM leads WHERE status != 'ignorado'"
            ).fetchone()["c"]
            por_status_maps = {
                linha["status"]: linha["c"]
                for linha in conexao.execute(
                    "SELECT status, COUNT(*) c FROM leads WHERE status != 'ignorado' GROUP BY status"
                ).fetchall()
            }
        hoje_local = date.today().isoformat()
        lembretes_maps = conexao.execute(
            "SELECT COUNT(*) c FROM leads WHERE status != 'ignorado' AND proximo_followup IS NOT NULL "
            "AND proximo_followup <= ?",
            (hoje_local,),
        ).fetchone()["c"] if db.CAMINHO_BANCO.exists() else 0

        total_instagram = conexao.execute(
            "SELECT COUNT(*) c FROM instagram_leads WHERE status != 'ignorado'"
        ).fetchone()["c"]
        por_status_instagram = {
            linha["status"]: linha["c"]
            for linha in conexao.execute(
                "SELECT status, COUNT(*) c FROM instagram_leads WHERE status != 'ignorado' GROUP BY status"
            ).fetchall()
        }
        lembretes_instagram = conexao.execute(
            "SELECT COUNT(*) c FROM instagram_leads WHERE status != 'ignorado' AND proximo_followup IS NOT NULL "
            "AND proximo_followup <= ?",
            (hoje_local,),
        ).fetchone()["c"]
    finally:
        conexao.close()

    total = total_maps + total_instagram
    por_status_combinado = dict(por_status_maps)
    for status, contagem in por_status_instagram.items():
        por_status_combinado[status] = por_status_combinado.get(status, 0) + contagem
    fechados = por_status_combinado.get("fechou", 0)
    taxa_conversao = round(100 * fechados / total, 1) if total else 0

    return jsonify({
        "total": total,
        "por_status": por_status_combinado,
        "taxa_conversao": taxa_conversao,
        "lembretes_hoje": lembretes_maps + lembretes_instagram,
        "maps": {"total": total_maps, "lembretes_hoje": lembretes_maps},
        "instagram": {"total": total_instagram, "lembretes_hoje": lembretes_instagram},
    })


CHAVE_CONFIG_META_SEMANAL = "meta_semanal_contatos"


def inicio_semana_atual_iso():
    """Segunda-feira desta semana, à meia-noite, em formato ISO - início do
    período que a meta semanal de contatos considera."""
    hoje = date.today()
    segunda = hoje - timedelta(days=hoje.weekday())
    return datetime.combine(segunda, datetime.min.time()).isoformat(timespec="seconds")


@bp.route("/api/meta-semanal")
def obter_meta_semanal():
    """Retorna a meta semanal configurada (leads contatados) e o progresso desde
    a última segunda-feira, contando transições para 'contatado' nos dois canais."""
    meta_str = db.obter_config(CHAVE_CONFIG_META_SEMANAL)
    meta = int(meta_str) if meta_str and meta_str.isdigit() else 0

    inicio_semana = inicio_semana_atual_iso()
    conexao = db.conectar()
    try:
        contatos_maps = conexao.execute(
            "SELECT COUNT(*) c FROM historico_status WHERE status_novo = 'contatado' AND alterado_em >= ?",
            (inicio_semana,),
        ).fetchone()["c"]
        contatos_instagram = conexao.execute(
            "SELECT COUNT(*) c FROM historico_status_instagram WHERE status_novo = 'contatado' AND alterado_em >= ?",
            (inicio_semana,),
        ).fetchone()["c"]
    finally:
        conexao.close()

    progresso = contatos_maps + contatos_instagram
    return jsonify({
        "meta": meta,
        "progresso": progresso,
        "faltam": max(meta - progresso, 0) if meta else 0,
        "porcentagem": round(100 * progresso / meta, 1) if meta else 0,
        "inicio_semana": inicio_semana[:10],
    })


@bp.route("/api/meta-semanal", methods=["POST"])
def salvar_meta_semanal():
    dados = request.json or {}
    meta = dados.get("meta")

    if not isinstance(meta, int) or meta < 0:
        return jsonify({"erro": "meta deve ser um número inteiro maior ou igual a 0"}), 400

    db.salvar_config(CHAVE_CONFIG_META_SEMANAL, str(meta))
    return jsonify({"ok": True, "meta": meta})


@bp.route("/api/tarefas-hoje")
def tarefas_hoje():
    """A "mesa de trabalho" do dia: follow-ups vencidos/para hoje (dos dois canais)
    + os leads novos mais quentes por score - cada item já vem com o link de
    WhatsApp/Instagram e a mensagem pronta, pra abordagem em 1 clique."""
    from rotas_leads import SQL_SCORE, calcular_score

    hoje_local = date.today().isoformat()
    conexao = db.conectar()
    try:
        followups_maps = [
            db.linha_para_dict(l) for l in conexao.execute(
                "SELECT place_id AS id, nome AS titulo, 'maps' AS canal, status, proximo_followup, "
                "follow_ups_enviados, ultimo_followup_em, whatsapp_link, telefone, "
                "mensagem_gerada AS mensagem, instagram_url "
                "FROM leads WHERE status != 'ignorado' AND proximo_followup IS NOT NULL "
                "AND proximo_followup <= ? ORDER BY proximo_followup",
                (hoje_local,),
            ).fetchall()
        ] if db.CAMINHO_BANCO.exists() else []

        followups_instagram = [
            db.linha_para_dict(l) for l in conexao.execute(
                "SELECT id, username, ('@' || username) AS titulo, 'instagram' AS canal, status, "
                "proximo_followup, follow_ups_enviados, ultimo_followup_em, "
                "sugestao_dm AS mensagem "
                "FROM instagram_leads WHERE status != 'ignorado' AND proximo_followup IS NOT NULL "
                "AND proximo_followup <= ? ORDER BY proximo_followup",
                (hoje_local,),
            ).fetchall()
        ]

        novos_quentes = [
            db.linha_para_dict(l) for l in conexao.execute(
                "SELECT place_id AS id, nome AS titulo, 'maps' AS canal, categoria, nota, "
                "num_avaliacoes, site_status, site_problemas, whatsapp_link, telefone, "
                "mensagem_gerada AS mensagem, instagram_url, nicho "
                f"FROM leads WHERE status = 'novo' ORDER BY {SQL_SCORE} DESC, nota DESC LIMIT 5",
            ).fetchall()
        ] if db.CAMINHO_BANCO.exists() else []
    finally:
        conexao.close()

    for lead in novos_quentes:
        # mesmos campos que o SQL_SCORE usou pra ordenar acima - senão o número
        # exibido podia não bater com a posição na lista
        lead["score"] = calcular_score(
            lead.get("nota"), lead.get("num_avaliacoes"), lead.get("site_status"),
            site_problemas=lead.get("site_problemas"), instagram_url=lead.get("instagram_url"),
            nicho=lead.get("nicho"),
        )

    followups = sorted(
        followups_maps + followups_instagram, key=lambda l: l["proximo_followup"]
    )
    return jsonify({"followups": followups, "novos_quentes": novos_quentes})


@bp.route("/api/follow-ups-hoje")
def follow_ups_hoje():
    """Lista os leads com follow-up vencido ou para hoje, dos dois canais juntos -
    ordenados pela data do follow-up (mais atrasado primeiro)."""
    conexao = db.conectar()
    try:
        hoje_local = date.today().isoformat()
        leads_maps = []
        if db.CAMINHO_BANCO.exists():
            leads_maps = [
                db.linha_para_dict(l) for l in conexao.execute(
                    "SELECT place_id, nome AS titulo, proximo_followup, status, 'maps' AS canal "
                    "FROM leads WHERE status != 'ignorado' AND proximo_followup IS NOT NULL "
                    "AND proximo_followup <= ? ORDER BY proximo_followup",
                    (hoje_local,),
                ).fetchall()
            ]
        leads_instagram = [
            db.linha_para_dict(l) for l in conexao.execute(
                "SELECT id AS place_id, username AS titulo, proximo_followup, status, 'instagram' AS canal "
                "FROM instagram_leads WHERE status != 'ignorado' AND proximo_followup IS NOT NULL "
                "AND proximo_followup <= ? ORDER BY proximo_followup",
                (hoje_local,),
            ).fetchall()
        ]
    finally:
        conexao.close()

    combinados = sorted(leads_maps + leads_instagram, key=lambda l: l["proximo_followup"])
    return jsonify({"leads": combinados})
