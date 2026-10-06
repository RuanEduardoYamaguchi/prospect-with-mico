import { QueryCache, QueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { ApiError } from "@/services/httpClient"

function mensagemDoErro(erro: unknown): string {
  if (erro instanceof ApiError) return erro.message
  if (erro instanceof Error) return erro.message
  return "Ocorreu um erro inesperado."
}

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 10_000,
    },
    mutations: {
      onError: (erro) => toast.error(mensagemDoErro(erro)),
    },
  },
  queryCache: new QueryCache({
    onError: (erro) => toast.error(mensagemDoErro(erro)),
  }),
})
