import { useMutation } from "@tanstack/react-query"
import { toast } from "sonner"
import { importarService } from "@/services/importarService"
import { useInvalidarLeads } from "@/hooks/useInvalidarLeads"

export function useImportarKaptar() {
  const invalidarListaEMetricas = useInvalidarLeads()

  return useMutation({
    mutationFn: ({
      conteudo,
      nichoPadrao,
      cidadePadrao,
    }: {
      conteudo: string
      nichoPadrao?: string
      cidadePadrao?: string
    }) => importarService.kaptar(conteudo, nichoPadrao, cidadePadrao),
    onSuccess: (resultado) => {
      invalidarListaEMetricas()
      toast.success(
        `${resultado.importados} lead(s) novo(s), ${resultado.atualizados} atualizado(s).`
      )
    },
  })
}
