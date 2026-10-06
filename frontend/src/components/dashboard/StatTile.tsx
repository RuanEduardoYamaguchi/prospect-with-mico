import { cn } from "@/lib/utils"

interface StatTileProps {
  rotulo: string
  valor: string | number
  icone?: React.ReactNode
  variante?: "default" | "destaque" | "alerta"
}

export function StatTile({ rotulo, valor, icone, variante = "default" }: StatTileProps) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-border bg-card px-4 py-3.5 shadow-sm transition-colors hover:bg-accent/30">
      {icone && (
        <div
          className={cn(
            "flex size-9 shrink-0 items-center justify-center rounded-lg",
            variante === "destaque" && "bg-success/12 text-success",
            variante === "alerta" && "bg-warning/12 text-warning",
            variante === "default" && "bg-muted text-muted-foreground"
          )}
        >
          {icone}
        </div>
      )}
      <div className="min-w-0">
        <p className="truncate text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
          {rotulo}
        </p>
        <p
          className={cn(
            "text-2xl font-semibold leading-tight tracking-tight tabular-nums",
            variante === "destaque" && "text-success",
            variante === "alerta" && "text-warning"
          )}
        >
          {valor}
        </p>
      </div>
    </div>
  )
}
