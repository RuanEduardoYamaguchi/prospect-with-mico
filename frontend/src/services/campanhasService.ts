import { httpClient } from "@/services/httpClient"
import type {
  Campanha,
  CampanhasResposta,
  CriarCampanhaInput,
  FiltrosCampanha,
  PreviaCampanhaResposta,
} from "@/types/whatsapp"

export const campanhasService = {
  previa: (filtros: FiltrosCampanha, template: string, limite: number) =>
    httpClient.post<PreviaCampanhaResposta>("/api/campanhas/previa", {
      filtros,
      template,
      limite,
    }),

  criar: (input: CriarCampanhaInput) =>
    httpClient.post<{ campanha: Campanha }>("/api/campanhas", input),

  listar: () => httpClient.get<CampanhasResposta>("/api/campanhas"),

  parar: (id: number) =>
    httpClient.post<{ campanha: Campanha }>(`/api/campanhas/${id}/parar`),

  retomar: (id: number) =>
    httpClient.post<{ campanha: Campanha }>(`/api/campanhas/${id}/retomar`),

  descartar: (id: number) =>
    httpClient.post<{ campanha: Campanha }>(`/api/campanhas/${id}/descartar`),
}
