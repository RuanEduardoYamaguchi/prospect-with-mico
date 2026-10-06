import { History } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { EmptyStateCard } from "@/components/shared/EmptyStateCard"
import { COR_STATUS_CAMPANHA, LABEL_STATUS_CAMPANHA } from "@/lib/constants"
import { formatarDataHora } from "@/lib/formatters"
import type { Campanha } from "@/types/whatsapp"

interface HistoricoCampanhasTableProps {
  historico: Campanha[]
}

export function HistoricoCampanhasTable({ historico }: HistoricoCampanhasTableProps) {
  if (historico.length === 0) {
    return (
      <EmptyStateCard
        icone={<History className="size-5" />}
        titulo="Nenhuma campanha no histórico ainda"
      />
    )
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-muted/40 text-left text-xs text-muted-foreground">
            <th className="px-3 py-2 font-medium">Campanha</th>
            <th className="px-3 py-2 font-medium">Status</th>
            <th className="px-3 py-2 text-right font-medium">Enviados</th>
            <th className="px-3 py-2 text-right font-medium">Falhas</th>
            <th className="px-3 py-2 text-right font-medium">Pulados</th>
            <th className="px-3 py-2 font-medium">Criada em</th>
          </tr>
        </thead>
        <tbody>
          {historico.map((campanha) => (
            <tr key={campanha.id} className="border-b border-border last:border-0">
              <td className="px-3 py-2 font-medium">{campanha.nome}</td>
              <td className="px-3 py-2">
                <Badge variant="outline" className={COR_STATUS_CAMPANHA[campanha.status]}>
                  {LABEL_STATUS_CAMPANHA[campanha.status]}
                </Badge>
              </td>
              <td className="px-3 py-2 text-right tabular-nums">{campanha.enviados}</td>
              <td className="px-3 py-2 text-right tabular-nums">{campanha.falhas}</td>
              <td className="px-3 py-2 text-right tabular-nums">{campanha.pulados}</td>
              <td className="px-3 py-2 text-muted-foreground">
                {formatarDataHora(campanha.criada_em)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
