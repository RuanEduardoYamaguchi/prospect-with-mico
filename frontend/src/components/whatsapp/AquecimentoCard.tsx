import { Flame, TriangleAlert } from "lucide-react"
import { Skeleton } from "@/components/ui/skeleton"
import { useAquecimento } from "@/hooks/useWhatsapp"

export function AquecimentoCard() {
  const { data, isLoading } = useAquecimento()

  if (isLoading || !data) return <Skeleton className="h-[140px] rounded-xl" />

  const percentual =
    data.teto_hoje > 0 ? Math.min(100, Math.round((data.enviados_hoje / data.teto_hoje) * 100)) : 0

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Flame className="size-4 text-muted-foreground" />
          <h3 className="font-medium">Aquecimento do chip</h3>
        </div>
        <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
          Dia {data.dia_do_chip}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="rounded-lg bg-muted/40 p-2">
          <p className="text-lg font-semibold tabular-nums">{data.enviados_hoje}</p>
          <p className="text-xs text-muted-foreground">enviados hoje</p>
        </div>
        <div className="rounded-lg bg-muted/40 p-2">
          <p className="text-lg font-semibold tabular-nums text-success">
            {data.restantes_hoje}
          </p>
          <p className="text-xs text-muted-foreground">restantes hoje</p>
        </div>
        <div className="rounded-lg bg-muted/40 p-2">
          <p className="text-lg font-semibold tabular-nums">{data.teto_hoje}</p>
          <p className="text-xs text-muted-foreground">teto de hoje</p>
        </div>
      </div>

      <div className="h-2 overflow-hidden rounded-full bg-border">
        <div
          className="h-full rounded-full bg-primary transition-all"
          style={{ width: `${percentual}%` }}
        />
      </div>

      {data.falhas_ontem >= 5 && (
        <p className="flex items-center gap-1.5 text-xs text-warning">
          <TriangleAlert className="size-3.5 shrink-0" />
          {data.falhas_ontem} falha(s) ontem - o teto não sobe num dia com 5 ou
          mais falhas.
        </p>
      )}
    </div>
  )
}
