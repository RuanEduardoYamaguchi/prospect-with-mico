import { useInfiniteQuery } from "@tanstack/react-query"
import { leadsService } from "@/services/leadsService"
import type { FiltrosLeads, Lead } from "@/types/lead"

const TAMANHO_PAGINA = 30

export function useLeads(filtros: FiltrosLeads) {
  const query = useInfiniteQuery({
    queryKey: ["leads", filtros],
    queryFn: ({ pageParam }) => leadsService.listar(filtros, pageParam),
    initialPageParam: 0,
    getNextPageParam: (paginaAtual, todasPaginas) =>
      paginaAtual.tem_mais ? todasPaginas.length * TAMANHO_PAGINA : undefined,
  })

  const leads: Lead[] = query.data?.pages.flatMap((p) => p.leads) ?? []

  return { ...query, leads }
}
