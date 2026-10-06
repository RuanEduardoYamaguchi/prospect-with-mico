import type { StatusLead } from "@/types/lead"

export interface Metricas {
  total: number
  por_status: Partial<Record<StatusLead, number>>
  taxa_conversao: number
  lembretes_hoje?: number
}
