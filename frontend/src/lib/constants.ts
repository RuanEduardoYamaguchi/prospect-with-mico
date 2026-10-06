import type { StatusLead } from "@/types/lead"
import type { StatusCampanha } from "@/types/whatsapp"

export const LABEL_STATUS: Record<StatusLead, string> = {
  novo: "Novo",
  contatado: "Contatado",
  respondeu: "Respondeu",
  fechou: "Fechou",
  recusou: "Recusou",
  ignorado: "Ignorado",
}

export const COR_STATUS: Record<StatusLead, string> = {
  novo: "bg-info/15 text-info border-info/30",
  contatado: "bg-warning/15 text-warning border-warning/30",
  respondeu: "bg-status-purple/15 text-status-purple border-status-purple/30",
  fechou: "bg-success/15 text-success border-success/30",
  recusou: "bg-destructive/15 text-destructive border-destructive/30",
  ignorado: "bg-muted text-muted-foreground border-border",
}

export const LABEL_STATUS_CAMPANHA: Record<StatusCampanha, string> = {
  rodando: "Rodando",
  pausada: "Pausada",
  concluida: "Concluída",
  parada: "Descartada",
  interrompida: "Interrompida",
}

export const COR_STATUS_CAMPANHA: Record<StatusCampanha, string> = {
  rodando: "bg-success/15 text-success border-success/30",
  pausada: "bg-warning/15 text-warning border-warning/30",
  concluida: "bg-info/15 text-info border-info/30",
  parada: "bg-muted text-muted-foreground border-border",
  interrompida: "bg-destructive/15 text-destructive border-destructive/30",
}

export const OPCOES_NOTA_MINIMA = [
  { valor: "", label: "Qualquer nota" },
  { valor: "4", label: "Nota ≥ 4.0" },
  { valor: "4.5", label: "Nota ≥ 4.5" },
  { valor: "5", label: "Nota = 5.0" },
] as const
