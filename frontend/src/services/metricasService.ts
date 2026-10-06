import { httpClient } from "@/services/httpClient"
import type { Metricas } from "@/types/metricas"

export const metricasService = {
  buscar: () => httpClient.get<Metricas>("/api/metricas"),
}
