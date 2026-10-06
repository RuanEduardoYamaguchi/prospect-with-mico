import { httpClient } from "@/services/httpClient"
import type {
  Aquecimento,
  ConectarWhatsappResposta,
  EnviarMensagemResposta,
  EnviarNumeroResposta,
  EstadoWhatsapp,
} from "@/types/whatsapp"

export const whatsappService = {
  estado: () => httpClient.get<EstadoWhatsapp>("/api/whatsapp/estado"),

  conectar: () => httpClient.post<ConectarWhatsappResposta>("/api/whatsapp/conectar"),

  desconectar: () => httpClient.post<{ ok: true }>("/api/whatsapp/desconectar"),

  autoresposta: () => httpClient.get<{ ativa: boolean }>("/api/whatsapp/autoresposta"),

  definirAutoresposta: (ativa: boolean) =>
    httpClient.post<{ ativa: boolean }>("/api/whatsapp/autoresposta", { ativa }),

  aquecimento: () => httpClient.get<Aquecimento>("/api/whatsapp/aquecimento"),

  enviar: (placeId: string, texto: string, followup = false) =>
    httpClient.post<EnviarMensagemResposta>("/api/whatsapp/enviar", {
      place_id: placeId,
      texto,
      followup,
    }),

  enviarNumero: (telefone: string, texto: string) =>
    httpClient.post<EnviarNumeroResposta>("/api/whatsapp/enviar-numero", {
      telefone,
      texto,
    }),
}
