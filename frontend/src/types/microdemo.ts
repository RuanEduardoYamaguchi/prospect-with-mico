export type RecomendacaoOportunidade = "abordar_com_demo" | "abordar_sem_demo" | "nao_abordar"
export type TipoMicroDemo = "agendamento" | "pedido" | "nenhuma"
export type ConfiancaAnalise = "alta" | "media" | "baixa"

export interface AnaliseOportunidade {
  recomendacao: RecomendacaoOportunidade
  oportunidade: string
  evidencias: string[]
  impacto: string
  solucao: string
  micro_demo: TipoMicroDemo
  confianca: ConfiancaAnalise
  motivo_nao_abordar: string
  desconhecido: string[]
  angulo: string
  provedor: string
  avisos: string[]
  criada_em: string
  score_no_momento: number
}

export interface OportunidadeResposta {
  analise: AnaliseOportunidade | null
  score: number
  score_min: number
}

export const LABEL_RECOMENDACAO: Record<RecomendacaoOportunidade, string> = {
  abordar_com_demo: "Abordar com demo",
  abordar_sem_demo: "Abordar sem demo",
  nao_abordar: "Não abordar",
}

export const COR_RECOMENDACAO: Record<RecomendacaoOportunidade, string> = {
  abordar_com_demo: "bg-success/15 text-success",
  abordar_sem_demo: "bg-info/15 text-info",
  nao_abordar: "bg-warning/15 text-warning",
}

export const LABEL_CONFIANCA: Record<ConfiancaAnalise, string> = {
  alta: "Confiança alta",
  media: "Confiança média",
  baixa: "Confiança baixa",
}

export const COR_CONFIANCA: Record<ConfiancaAnalise, string> = {
  alta: "bg-success/15 text-success",
  media: "bg-info/15 text-info",
  baixa: "bg-warning/15 text-warning",
}

export const LABEL_MICRO_DEMO: Record<TipoMicroDemo, string> = {
  agendamento: "Demo de agendamento",
  pedido: "Demo de pedido",
  nenhuma: "Nenhum modelo pronto, demo manual",
}
