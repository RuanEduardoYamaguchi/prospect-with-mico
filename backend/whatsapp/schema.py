"""Migração aditiva do WhatsApp: a coluna `leads.wa_optout` e as tabelas
`wa_envios`, `wa_campanhas`, `wa_fila`. Espelha o estilo de `processar.migrar_banco`:
roda toda vez que o app sobe, é seguro rodar múltiplas vezes (idempotente) e
nunca recria/apaga tabelas ou dados existentes.

Contrato completo (colunas, valores válidos de status/estado) em
`docs/INTEGRACAO.md`.
"""


def preparar(conexao):
    colunas_leads = {linha[1] for linha in conexao.execute("PRAGMA table_info(leads)")}
    if "wa_optout" not in colunas_leads:
        conexao.execute("ALTER TABLE leads ADD COLUMN wa_optout INTEGER NOT NULL DEFAULT 0")
    if "wa_ia_pausada" not in colunas_leads:
        conexao.execute("ALTER TABLE leads ADD COLUMN wa_ia_pausada INTEGER NOT NULL DEFAULT 0")

    # Uma linha por tentativa de envio (individual ou de campanha) - é o que
    # garante "nunca manda duas vezes pro mesmo número" e alimenta o
    # aquecimento (conta envios/falhas por dia).
    conexao.execute(
        """
        CREATE TABLE IF NOT EXISTS wa_envios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            place_id TEXT NOT NULL,
            telefone TEXT NOT NULL,
            texto TEXT NOT NULL,
            status TEXT NOT NULL,
            erro TEXT,
            campanha_id INTEGER,
            id_externo TEXT,
            enviado_em TEXT NOT NULL
        )
        """
    )

    # Uma linha por campanha disparada. `config_json` guarda filtros + ritmo +
    # checar_whatsapp (não vira coluna própria: evita migração toda vez que um
    # campo novo de configuração aparece). Estado 100% no banco, de propósito:
    # é o que permite sobreviver a um restart do backend (ver campanha.py).
    conexao.execute(
        """
        CREATE TABLE IF NOT EXISTS wa_campanhas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            template TEXT NOT NULL,
            config_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'rodando',
            total INTEGER NOT NULL DEFAULT 0,
            enviados INTEGER NOT NULL DEFAULT 0,
            falhas INTEGER NOT NULL DEFAULT 0,
            pulados INTEGER NOT NULL DEFAULT 0,
            criada_em TEXT NOT NULL,
            atualizada_em TEXT,
            finalizada_em TEXT,
            ultimo_erro TEXT
        )
        """
    )

    # A fila de uma campanha, na ordem em que vai ser processada. `estado`
    # pendente→enviado/falhou/pulado é o que permite retomar depois de um
    # restart sem reprocessar quem já foi atendido.
    conexao.execute(
        """
        CREATE TABLE IF NOT EXISTS wa_fila (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campanha_id INTEGER NOT NULL,
            place_id TEXT NOT NULL,
            telefone TEXT NOT NULL,
            ordem INTEGER NOT NULL,
            estado TEXT NOT NULL DEFAULT 'pendente',
            texto TEXT NOT NULL
        )
        """
    )

    conexao.execute("CREATE INDEX IF NOT EXISTS idx_wa_envios_place_id ON wa_envios(place_id)")
    conexao.execute("CREATE INDEX IF NOT EXISTS idx_wa_envios_telefone ON wa_envios(telefone)")
    conexao.execute("CREATE INDEX IF NOT EXISTS idx_wa_envios_campanha ON wa_envios(campanha_id)")
    conexao.execute("CREATE INDEX IF NOT EXISTS idx_wa_envios_status_data ON wa_envios(status, enviado_em)")
    conexao.execute("CREATE INDEX IF NOT EXISTS idx_wa_fila_campanha_ordem ON wa_fila(campanha_id, ordem)")
    conexao.execute("CREATE INDEX IF NOT EXISTS idx_wa_fila_campanha_estado ON wa_fila(campanha_id, estado)")
    conexao.execute("CREATE INDEX IF NOT EXISTS idx_wa_campanhas_status ON wa_campanhas(status)")
    conexao.commit()
