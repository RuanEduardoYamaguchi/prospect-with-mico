import type { StatusLead } from "@/types/lead"

export interface EstagioFunil {
  status: StatusLead
  total: number
}

export interface FunilResposta {
  estagios: EstagioFunil[]
}

export interface NichoAnalytics {
  nicho: string
  total: number
  fechados: number
  taxa_conversao: number
}

export interface PorNichoResposta {
  nichos: NichoAnalytics[]
}
