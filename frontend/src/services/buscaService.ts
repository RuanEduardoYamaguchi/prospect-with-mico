import { httpClient } from "@/services/httpClient"
import type { AreaBuscaPayload, BuscaHistorico, EstadoBusca } from "@/types/busca"

export const buscaService = {
  disparar: (queries: string) =>
    httpClient.post<{ ok: true }>("/api/buscar", { queries }),

  dispararPorMapa: (nichos: string[], areas: AreaBuscaPayload[]) =>
    httpClient.post<{ ok: true }>("/api/buscar", { nichos, areas }),

  consultarStatus: () => httpClient.get<EstadoBusca>("/api/buscar/status"),

  historico: () =>
    httpClient.get<{ buscas: BuscaHistorico[] }>("/api/buscar/historico"),
}
