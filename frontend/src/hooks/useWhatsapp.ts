import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { whatsappService } from "@/services/whatsappService"

export const CHAVE_ESTADO_WHATSAPP = ["whatsapp-estado"]
export const CHAVE_AQUECIMENTO = ["whatsapp-aquecimento"]
export const CHAVE_AUTORESPOSTA = ["whatsapp-autoresposta"]

export function useAutoresposta() {
  return useQuery({
    queryKey: CHAVE_AUTORESPOSTA,
    queryFn: whatsappService.autoresposta,
  })
}

export function useDefinirAutoresposta() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (ativa: boolean) => whatsappService.definirAutoresposta(ativa),
    onSuccess: ({ ativa }) => {
      queryClient.setQueryData(CHAVE_AUTORESPOSTA, { ativa })
      toast.success(ativa ? "IA respondendo os leads." : "Resposta automática desligada.")
    },
    onError: (erro: Error) => toast.error(erro.message),
  })
}

/** Enquanto não está conectado, repete a cada 5s pra pegar o QR sendo lido no
 * celular ou a Evolution voltando do ar. Conectado, não precisa mais insistir. */
export function useEstadoWhatsapp() {
  return useQuery({
    queryKey: CHAVE_ESTADO_WHATSAPP,
    queryFn: whatsappService.estado,
    refetchInterval: (query) => (query.state.data?.conectado ? false : 5000),
  })
}

export function useAquecimento() {
  return useQuery({
    queryKey: CHAVE_AQUECIMENTO,
    queryFn: whatsappService.aquecimento,
  })
}

export function useConectarWhatsapp() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: whatsappService.conectar,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CHAVE_ESTADO_WHATSAPP })
    },
  })
}

export function useDesconectarWhatsapp() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: whatsappService.desconectar,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CHAVE_ESTADO_WHATSAPP })
      queryClient.invalidateQueries({ queryKey: CHAVE_AQUECIMENTO })
      toast.success("WhatsApp desconectado.")
    },
  })
}

export function useEnviarNumeroWhatsapp() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ telefone, texto }: { telefone: string; texto: string }) =>
      whatsappService.enviarNumero(telefone, texto),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CHAVE_AQUECIMENTO })
      toast.success("Mensagem enviada pelo WhatsApp.")
    },
  })
}
