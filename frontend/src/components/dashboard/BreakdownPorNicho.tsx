import { PieChart } from "lucide-react"
import { Skeleton } from "@/components/ui/skeleton"
import { EmptyStateCard } from "@/components/shared/EmptyStateCard"
import type { NichoAnalytics } from "@/types/analytics"

interface BreakdownPorNichoProps {
  nichos: NichoAnalytics[] | undefined
  isLoading: boolean
  corBarra: string
}

export function BreakdownPorNicho({
  nichos,
  isLoading,
  corBarra,
}: BreakdownPorNichoProps) {
  if (isLoading || !nichos) {
    return <Skeleton className="h-[280px]" />
  }

  if (nichos.length === 0) {
    return (
      <div className="rounded-xl border border-border bg-card p-4">
        <h3 className="mb-4 text-sm font-medium text-muted-foreground">
          Conversão por nicho
        </h3>
        <EmptyStateCard
          icone={<PieChart className="size-5" />}
          titulo="Nenhum nicho ainda"
          descricao="Os nichos vêm das suas buscas (ex.: 'clínica de estética em Londrina') - rode uma busca para começar a comparar a conversão por nicho."
          className="h-[240px] border-0 bg-transparent"
        />
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <h3 className="mb-4 text-sm font-medium text-muted-foreground">
        Conversão por nicho
      </h3>
      <div className="max-h-[240px] space-y-3 overflow-y-auto pr-1">
        {nichos.map((n) => (
          <div key={n.nicho}>
            <div className="mb-1 flex items-center justify-between gap-2 text-sm">
              <span className="truncate">{n.nicho}</span>
              <span className="shrink-0 text-muted-foreground">
                {n.fechados}/{n.total} · {n.taxa_conversao}%
              </span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-muted">
              <div
                className={`h-full rounded-full ${corBarra}`}
                style={{ width: `${n.taxa_conversao}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
