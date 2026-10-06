import { useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { leadsService } from "@/services/leadsService"
import { whatsappService } from "@/services/whatsappService"
import { useInvalidarLeads } from "@/hooks/useInvalidarLeads"
import { CHAVE_AQUECIMENTO } from "@/hooks/useWhatsapp"
import { tocarSom } from "@/hooks/useSom"
import type { AbordagemContato, StatusLead } from "@/types/lead"

interface EstadoFollowupAnterior {
  followUpsEnviadosAnterior: number
  ultimoFollowupEmAnterior: string | null
  proximoFollowupAnterior: string | null
}

export function useLeadMutations(placeId: string) {
  const invalidarListaEMetricas = useInvalidarLeads()
  const queryClient = useQueryClient()

  const atualizarStatus = useMutation({
    mutationFn: (status: StatusLead) =>
      leadsService.atualizarStatus(placeId, status),
    onSuccess: (_dados, status) => {
      invalidarListaEMetricas()
      if (status === "fechou") tocarSom("lead-fechou")
      toast.success("Status atualizado.")
    },
  })

  const salvarTagsFollowup = useMutation({
    mutationFn: (input: { tags: string; proximoFollowup: string | null }) =>
      Promise.all([
        leadsService.atualizarTags(placeId, input.tags),
        leadsService.atualizarFollowup(placeId, input.proximoFollowup),
      ]),
    onSuccess: () => {
      invalidarListaEMetricas()
      toast.success("Tags e follow-up salvos.")
    },
  })

  const salvarObservacoes = useMutation({
    mutationFn: (observacoes: string) =>
      leadsService.atualizarObservacoes(placeId, observacoes),
    onSuccess: () => toast.success("Observações salvas."),
  })

  const gerarMensagem = useMutation({
    mutationFn: ({
      forcarNova,
      tipo,
      abordagem,
    }: {
      forcarNova: boolean
      tipo?: "contato" | "followup"
      abordagem?: AbordagemContato
    }) => leadsService.gerarMensagem(placeId, forcarNova, tipo, abordagem),
  })

  const marcarFollowupEnviado = useMutation({
    mutationFn: (estadoAnterior: EstadoFollowupAnterior) =>
      leadsService.marcarFollowupEnviado(placeId).then((resposta) => ({
        resposta,
        estadoAnterior,
      })),
    onSuccess: ({ resposta, estadoAnterior }) => {
      invalidarListaEMetricas()
      tocarSom("followup-marcado")
      toast.success(`Follow-up nº ${resposta.follow_ups_enviados} registrado.`, {
        action: {
          label: "Desfazer",
          onClick: () => {
            leadsService
              .desfazerFollowupEnviado(placeId, estadoAnterior)
              .then(() => {
                invalidarListaEMetricas()
                toast.success("Follow-up desfeito.")
              })
          },
        },
      })
    },
  })

  const ignorar = useMutation({
    mutationFn: (statusAnterior: StatusLead) => leadsService.ignorar(placeId).then(() => statusAnterior),
    onSuccess: (statusAnterior) => {
      invalidarListaEMetricas()
      toast("Lead ignorado.", {
        action: {
          label: "Desfazer",
          onClick: () => {
            leadsService.atualizarStatus(placeId, statusAnterior).then(() => {
              invalidarListaEMetricas()
              toast.success("Lead restaurado.")
            })
          },
        },
      })
    },
  })

  const reanalisarSite = useMutation({
    mutationFn: () => leadsService.reanalisarSite(placeId),
    onSuccess: (resultado) => {
      invalidarListaEMetricas()
      const rotulos = { sem_site: "sem site", site_ruim: "site ruim", site_ok: "site ok" }
      const detalhe = resultado.site_problemas ? ` - ${resultado.site_problemas}` : ""
      toast.success(`Site reanalisado: ${rotulos[resultado.site_status]}${detalhe}`)
    },
  })

  const enviarWhatsapp = useMutation({
    mutationFn: (entrada: string | { texto: string; followup?: boolean }) =>
      typeof entrada === "string"
        ? whatsappService.enviar(placeId, entrada)
        : whatsappService.enviar(placeId, entrada.texto, entrada.followup),
    onSuccess: () => {
      invalidarListaEMetricas()
      queryClient.invalidateQueries({ queryKey: ["conversa", "maps", placeId] })
      queryClient.invalidateQueries({ queryKey: CHAVE_AQUECIMENTO })
      tocarSom("card-movido")
      toast.success("Mensagem enviada pelo WhatsApp.")
    },
  })

  const definirIaPausada = useMutation({
    mutationFn: (pausada: boolean) => leadsService.definirIaPausada(placeId, pausada),
    onSuccess: ({ pausada }) => {
      queryClient.invalidateQueries({ queryKey: ["lead", placeId] })
      invalidarListaEMetricas()
      toast.success(pausada ? "IA pausada neste lead." : "IA respondendo este lead.")
    },
    onError: (erro: Error) => toast.error(erro.message),
  })

  const excluirDefinitivamente = useMutation({
    mutationFn: () => leadsService.excluirDefinitivamente(placeId),
    onSuccess: () => {
      invalidarListaEMetricas()
      tocarSom("apagar-lead")
      toast.success("Lead excluído definitivamente.")
    },
  })

  return {
    atualizarStatus,
    salvarTagsFollowup,
    salvarObservacoes,
    gerarMensagem,
    marcarFollowupEnviado,
    ignorar,
    reanalisarSite,
    enviarWhatsapp,
    definirIaPausada,
    excluirDefinitivamente,
  }
}
