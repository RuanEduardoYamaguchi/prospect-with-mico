import { useQuery } from "@tanstack/react-query"
import { analyticsService } from "@/services/analyticsService"

export function useFunil() {
  return useQuery({
    queryKey: ["analytics", "funil"],
    queryFn: analyticsService.funil,
  })
}

export function usePorNicho() {
  return useQuery({
    queryKey: ["analytics", "por-nicho"],
    queryFn: analyticsService.porNicho,
  })
}
