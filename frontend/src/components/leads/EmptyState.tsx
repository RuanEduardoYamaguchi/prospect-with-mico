import { Inbox, Plus } from "lucide-react"
import { Button } from "@/components/ui/button"

interface EmptyStateProps {
  filtrosEmUso: boolean
  onLimparFiltros: () => void
  onNovaBusca?: () => void
}

export function EmptyState({
  filtrosEmUso,
  onLimparFiltros,
  onNovaBusca,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border py-16 text-center">
      <Inbox className="size-8 text-muted-foreground" />
      {filtrosEmUso ? (
        <>
          <p className="text-sm text-muted-foreground">
            Nenhum lead encontrado com esses filtros.
          </p>
          <Button variant="outline" size="sm" onClick={onLimparFiltros}>
            Limpar filtros
          </Button>
        </>
      ) : (
        <>
          <p className="text-sm text-muted-foreground">
            Nenhuma busca foi feita ainda.
          </p>
          <p className="max-w-xs text-xs text-muted-foreground">
            Cada linha da busca é um nicho + cidade, por exemplo:{" "}
            <span className="font-medium text-foreground">
              "clínica de estética em Londrina"
            </span>
          </p>
          {onNovaBusca && (
            <Button size="sm" onClick={onNovaBusca}>
              <Plus className="size-4" />
              Nova busca
            </Button>
          )}
        </>
      )}
    </div>
  )
}
