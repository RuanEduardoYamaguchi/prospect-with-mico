export type StatusLead =
  | "novo"
  | "contatado"
  | "respondeu"
  | "fechou"
  | "recusou"
  | "ignorado"

export const STATUS_VALIDOS: StatusLead[] = [
  "novo",
  "contatado",
  "respondeu",
  "fechou",
  "recusou",
  "ignorado",
]

export interface Lead {
  place_id: string
  nome: string
  categoria: string | null
  endereco: string | null
  nota: number | null
  num_avaliacoes: number | null
  whatsapp_link: string | null
  telefone: string | null
  query_origem: string | null
  nicho: string | null
  cidade: string | null
  status: StatusLead
  observacoes: string | null
  mensagem_gerada: string | null
  visto_em: string | null
  atualizado_em: string | null
  tags: string | null
  proximo_followup: string | null
  follow_ups_enviados: number
  ultimo_followup_em: string | null
  lead_dificil: boolean
  score: number
  site_url: string | null
  site_status: "sem_site" | "site_ruim" | "site_ok" | null
  site_problemas: string | null
  site_checklist: { tem: string[]; falta: string[] } | null
  instagram_url: string | null
  wa_ia_pausada?: number | boolean
}

export interface HistoricoStatusItem {
  status_anterior: StatusLead | null
  status_novo: StatusLead
  alterado_em: string
}

export interface FiltrosLeads {
  busca: string
  status: StatusLead | ""
  nicho: string
  nota_min: "" | "4" | "4.5" | "5"
  ordenar: "" | "score"
  site_status: "" | "sem_site" | "site_ruim" | "site_ok"
  /** Não aparece na barra de filtros - usado pela fila da sessão de prospecção */
  followup: "" | "vencido"
}

export const FILTROS_VAZIOS: FiltrosLeads = {
  busca: "",
  status: "",
  nicho: "",
  nota_min: "",
  ordenar: "",
  site_status: "",
  followup: "",
}

/** Como o primeiro contato abre: "direta" argumenta e posiciona a oferta;
 * "print" só pede o responsável e oferece um print, sem vender nada. */
export type AbordagemContato = "direta" | "print"

export interface GerarMensagemResposta {
  mensagem: string
  cache: boolean
  provedor?: string
  avisos?: string[]
}

export interface RespostaMarcarFollowup {
  ok: true
  follow_ups_enviados: number
  ultimo_followup_em: string
  proximo_followup_sugerido: string
}

export interface PaginaLeads {
  leads: Lead[]
  tem_mais: boolean
}
