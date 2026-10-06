import { httpClient } from "@/services/httpClient"
import type { AnaliseOportunidade, OportunidadeResposta } from "@/types/microdemo"

const base = (placeId: string) => `/api/leads/${encodeURIComponent(placeId)}/oportunidade`

export const microdemoService = {
  obterOportunidade: (placeId: string) => httpClient.get<OportunidadeResposta>(base(placeId)),

  analisarOportunidade: (placeId: string) =>
    httpClient.post<{ analise: AnaliseOportunidade }>(`${base(placeId)}/analisar`),
}
