import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { microdemoService } from "@/services/microdemoService"

const chaveOportunidade = (placeId: string) => ["oportunidade", placeId]

export function useOportunidade(placeId: string, opcoes: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: chaveOportunidade(placeId),
    queryFn: () => microdemoService.obterOportunidade(placeId),
    enabled: opcoes.enabled ?? true,
  })
}

export function useAnalisarOportunidade(placeId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => microdemoService.analisarOportunidade(placeId),
    onSuccess: ({ analise }) => {
      queryClient.invalidateQueries({ queryKey: chaveOportunidade(placeId) })
      if (analise.avisos?.length) {
        toast.warning(`${analise.avisos.join(" ")} (usado: ${analise.provedor || "?"})`)
      } else {
        toast.success("Oportunidade analisada.")
      }
    },
    onError: (erro: Error) => toast.error(erro.message),
  })
}
