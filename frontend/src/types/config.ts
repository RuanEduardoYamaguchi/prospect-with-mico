export type ProvedorIA = "anthropic" | "gemini" | "groq" | "nvidia" | "pagespeed"

export interface ConfiguracaoProvedor {
  configurada: boolean
  mascarada: string | null
  link_obter_chave: string
}

export type Configuracoes = Record<ProvedorIA, ConfiguracaoProvedor>
