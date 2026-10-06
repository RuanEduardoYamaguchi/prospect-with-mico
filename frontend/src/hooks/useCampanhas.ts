import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { campanhasService } from "@/services/campanhasService"
import type { CriarCampanhaInput, FiltrosCampanha } from "@/types/whatsapp"

const CHAVE_CAMPANHAS = ["campanhas"]

/** Só insiste no polling enquanto tem campanha rodando - pausada, parada ou
 * sem campanha nenhuma não precisa martelar o servidor. */
export function useCampanhas() {
  return useQuery({
    queryKey: CHAVE_CAMPANHAS,
    queryFn: campanhasService.listar,
    refetchInterval: (query) =>
      query.state.data?.ativa?.status === "rodando" ? 3000 : false,
  })
}

export function usePreviaCampanha(
  filtros: FiltrosCampanha,
  template: string,
  limite: number,
  habilitado: boolean
) {
  return useQuery({
    queryKey: ["campanha-previa", filtros, template, limite],
    queryFn: () => campanhasService.previa(filtros, template, limite),
    enabled: habilitado,
    placeholderData: keepPreviousData,
  })
}

export function useCriarCampanha() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (input: CriarCampanhaInput) => campanhasService.criar(input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: CHAVE_CAMPANHAS })
      toast.success("Campanha iniciada.")
    },
  })
}

export function useCampanhaMutations(id: number | undefined) {
  const queryClient = useQueryClient()
  const invalidar = () => queryClient.invalidateQueries({ queryKey: CHAVE_CAMPANHAS })

  const parar = useMutation({
    mutationFn: () => campanhasService.parar(id!),
    onSuccess: () => {
      invalidar()
      toast.success("Campanha pausada.")
    },
  })

  const retomar = useMutation({
    mutationFn: () => campanhasService.retomar(id!),
    onSuccess: () => {
      invalidar()
      toast.success("Campanha retomada.")
    },
  })

  const descartar = useMutation({
    mutationFn: () => campanhasService.descartar(id!),
    onSuccess: () => {
      invalidar()
      toast.success("Campanha descartada.")
    },
  })

  return { parar, retomar, descartar }
}
