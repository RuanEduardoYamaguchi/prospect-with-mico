"""Migração aditiva da tabela `analises_oportunidade`. Idempotente, igual ao
`whatsapp/schema.py`: roda a cada subida do app e nunca apaga dados.

Listas (`evidencias`, `desconhecido`) ficam como JSON em TEXT.
"""


def preparar(conexao):
    conexao.execute(
        """
        CREATE TABLE IF NOT EXISTS analises_oportunidade (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            place_id TEXT NOT NULL,
            recomendacao TEXT NOT NULL,
            oportunidade TEXT,
            evidencias TEXT,
            impacto TEXT,
            solucao TEXT,
            micro_demo TEXT,
            confianca TEXT,
            motivo_nao_abordar TEXT,
            desconhecido TEXT,
            angulo TEXT,
            score_no_momento INTEGER,
            provedor TEXT,
            criada_em TEXT NOT NULL
        )
        """
    )
    conexao.execute(
        "CREATE INDEX IF NOT EXISTS idx_analises_oportunidade_place_id "
        "ON analises_oportunidade(place_id)"
    )
    conexao.commit()
