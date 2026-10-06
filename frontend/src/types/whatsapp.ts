export type EstadoConexao = "open" | "connecting" | "close" | "indisponivel"

export interface EstadoWhatsapp {
  evolution_ok: boolean
  conectado: boolean
  estado: EstadoConexao
  numero: string | null
  instancia: string
  /** true quando o chip conectado é o seu número oficial (NUMERO_OFICIAL): campanha bloqueada */
  numero_oficial?: boolean
  /** true quando é o número oficial mas a campanha foi liberada de propósito (teto 20/dia) */
  oficial_liberado?: boolean
}

export interface ConectarWhatsappResposta {
  estado: EstadoConexao
  /** Data URL (`data:image/png;base64,...`) ou null se já conectado */
  qr_base64: string | null
}

export interface Aquecimento {
  dia_do_chip: number
  teto_hoje: number
  enviados_hoje: number
  restantes_hoje: number
  falhas_ontem: number
}

export type StatusEnvio = "enviado" | "falhou" | "pulado"

export interface Envio {
  id: number
  place_id: string
  telefone: string
  texto: string
  status: StatusEnvio
  erro: string | null
  campanha_id: number | null
  id_externo: string | null
  enviado_em: string
}

export interface EnviarMensagemResposta {
  ok: true
  envio: Envio
}

export interface EnviarNumeroResposta {
  ok: true
  numero: string
}

export interface FiltrosCampanha {
  nicho: string | null
  cidade: string | null
  status: string[]
  score_min: number
  score_max: number
  sem_site: boolean
  sem_instagram: boolean
  max_avaliacoes: number | null
  so_celular: boolean
  pular_contatados: boolean
}

export const FILTROS_CAMPANHA_PADRAO: FiltrosCampanha = {
  nicho: null,
  cidade: null,
  status: ["novo"],
  score_min: 40,
  score_max: 69,
  sem_site: false,
  sem_instagram: false,
  max_avaliacoes: null,
  so_celular: true,
  pular_contatados: true,
}

export interface RitmoCampanha {
  intervalo_min_s: number
  intervalo_max_s: number
  pausa_a_cada: number
  pausa_s: number
  janela_inicio: string
  janela_fim: string
}

export const RITMO_CAMPANHA_PADRAO: RitmoCampanha = {
  intervalo_min_s: 45,
  intervalo_max_s: 120,
  pausa_a_cada: 10,
  pausa_s: 600,
  janela_inicio: "09:00",
  janela_fim: "18:00",
}

export interface LeadPreviaCampanha {
  place_id: string
  nome: string
  telefone: string
  nicho: string | null
  cidade: string | null
  score: number
  site_status: "sem_site" | "site_ruim" | "site_ok" | null
  texto_exemplo: string
}

export interface PreviaCampanhaResposta {
  leads: LeadPreviaCampanha[]
  total: number
  descartados: Record<string, number>
  teto_restante: number
  aviso: string | null
}

export type StatusCampanha = "rodando" | "pausada" | "concluida" | "parada" | "interrompida"

export interface EnvioResumoCampanha {
  nome: string
  telefone: string
  status: StatusEnvio
  enviado_em: string
}

export interface Campanha {
  id: number
  nome: string
  status: StatusCampanha
  template: string
  total: number
  enviados: number
  falhas: number
  pulados: number
  proximo_envio_em: string | null
  aguardando_janela: boolean
  ultimo_erro: string | null
  criada_em: string
  finalizada_em: string | null
  ultimos: EnvioResumoCampanha[]
}

export interface CampanhasResposta {
  ativa: Campanha | null
  historico: Campanha[]
}

export interface CriarCampanhaInput {
  nome?: string
  filtros: FiltrosCampanha
  template: string
  limite: number
  ritmo: RitmoCampanha
  checar_whatsapp: boolean
}

export interface ImportarKaptarResposta {
  importados: number
  atualizados: number
  descartados: Record<string, number>
}
