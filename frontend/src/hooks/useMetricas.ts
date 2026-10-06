import { useQuery } from "@tanstack/react-query"
import { metricasService } from "@/services/metricasService"

export function useMetricas() {
  return useQuery({
    queryKey: ["metricas"],
    queryFn: metricasService.buscar,
  })
}
