import { useQuery } from "@tanstack/react-query"
import { leadsService } from "@/services/leadsService"

export function useLeadHistorico(placeId: string, habilitado: boolean) {
  return useQuery({
    queryKey: ["lead-historico", placeId],
    queryFn: () => leadsService.historico(placeId),
    enabled: habilitado,
  })
}
