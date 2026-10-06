import { Loader2 } from "lucide-react"
import type { EstadoBusca } from "@/types/busca"

interface BuscaProgressProps {
  estado: EstadoBusca
}

export function BuscaProgress({ estado }: BuscaProgressProps) {
  const indeterminado = estado.etapa === "scraping"
  const percentual =
    estado.etapa === "verificando_sites" && estado.empresas_encontradas > 0
      ? Math.min(
          100,
          Math.round(
            (estado.empresas_processadas / estado.empresas_encontradas) * 100
          )
        )
      : 0

  return (
    <div className="space-y-2 rounded-lg border border-border bg-muted/40 p-3">
      <div className="flex items-center gap-2 text-sm">
        <Loader2 className="size-4 shrink-0 animate-spin text-primary" />
        <span className="min-w-0 flex-1">{estado.mensagem}</span>
        {estado.total_areas > 0 && estado.area_atual > 0 && (
          <span className="shrink-0 rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium tabular-nums text-primary">
            Área {estado.area_atual}/{estado.total_areas}
          </span>
        )}
      </div>

      {estado.etapa === "scraping" && (
        <p className="text-xs text-muted-foreground">
          Encontradas {estado.empresas_encontradas} · Processadas{" "}
          {estado.empresas_processadas}
        </p>
      )}

      <div className="h-2 overflow-hidden rounded-full bg-border">
        {indeterminado ? (
          <div className="h-full w-[30%] animate-[deslizar_1.2s_ease-in-out_infinite] rounded-full bg-primary" />
        ) : (
          <div
            className="h-full rounded-full bg-primary transition-all"
            style={{ width: `${percentual}%` }}
          />
        )}
      </div>
    </div>
  )
}
