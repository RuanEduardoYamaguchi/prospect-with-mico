import { httpClient } from "@/services/httpClient"
import type { ImportarKaptarResposta } from "@/types/whatsapp"

export const importarService = {
  kaptar: (conteudo: string, nichoPadrao?: string, cidadePadrao?: string) =>
    httpClient.post<ImportarKaptarResposta>("/api/importar/kaptar", {
      conteudo,
      nicho_padrao: nichoPadrao || undefined,
      cidade_padrao: cidadePadrao || undefined,
    }),
}
