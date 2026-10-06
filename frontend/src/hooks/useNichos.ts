import { useQuery } from "@tanstack/react-query"
import { nichosService } from "@/services/nichosService"

export function useNichos() {
  return useQuery({
    queryKey: ["nichos"],
    queryFn: nichosService.listar,
  })
}
