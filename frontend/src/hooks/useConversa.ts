import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { conversaService } from "@/services/conversaService"
import type { AutorMensagem } from "@/types/conversa"

const chaveConversa = (canal: string, leadRef: string) => ["conversa", canal, leadRef]

/** Histórico + última análise. Atualiza a cada 5s: as respostas do lead
 * chegam pelo webhook da Evolution e a IA também escreve na conversa. */
export function useConversa(canal: string, leadRef: string) {
  return useQuery({
    queryKey: chaveConversa(canal, leadRef),
    queryFn: () => conversaService.obter(canal, leadRef),
    refetchInterval: 5000,
  })
}

export function useConversaMutations(canal: string, leadRef: string) {
  const queryClient = useQueryClient()
  const invalidar = () =>
    queryClient.invalidateQueries({ queryKey: chaveConversa(canal, leadRef) })

  const adicionarMensagem = useMutation({
    mutationFn: (dados: { autor: AutorMensagem; texto: string }) =>
      conversaService.adicionarMensagem(canal, leadRef, dados),
    onSuccess: invalidar,
    onError: (erro: Error) => toast.error(erro.message),
  })

  const removerMensagem = useMutation({
    mutationFn: (mensagemId: number) =>
      conversaService.removerMensagem(canal, leadRef, mensagemId),
    onSuccess: invalidar,
    onError: (erro: Error) => toast.error(erro.message),
  })

  const analisar = useMutation({
    mutationFn: () => conversaService.analisar(canal, leadRef),
    onSuccess: (analise) => {
      invalidar()
      if (analise.avisos?.length) {
        toast.warning(`${analise.avisos.join(" ")} (usado: ${analise.provedor ?? "?"})`)
      } else {
        toast.success("Conversa analisada.")
      }
    },
    onError: (erro: Error) => toast.error(erro.message),
  })

  return { adicionarMensagem, removerMensagem, analisar }
}
