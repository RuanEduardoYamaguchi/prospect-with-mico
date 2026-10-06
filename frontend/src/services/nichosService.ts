import { httpClient } from "@/services/httpClient"

export const nichosService = {
  listar: () => httpClient.get<string[]>("/api/nichos"),
}
