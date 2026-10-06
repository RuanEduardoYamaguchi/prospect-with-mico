import { useQuery } from "@tanstack/react-query"
import { tarefasService } from "@/services/tarefasService"

export function useTarefasHoje() {
  const tarefas = useQuery({
    queryKey: ["tarefas-hoje"],
    queryFn: tarefasService.tarefasHoje,
  })

  return { tarefas }
}
