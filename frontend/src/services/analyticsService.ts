import { httpClient } from "@/services/httpClient"
import type { FunilResposta, PorNichoResposta } from "@/types/analytics"

export const analyticsService = {
  funil: () => httpClient.get<FunilResposta>("/api/analytics/funil"),
  porNicho: () => httpClient.get<PorNichoResposta>("/api/analytics/por-nicho"),
}
