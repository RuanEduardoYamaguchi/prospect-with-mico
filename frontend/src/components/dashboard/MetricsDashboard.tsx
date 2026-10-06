import { CheckCircle2, Clock, Handshake, MessageCircle, Percent, Users } from "lucide-react"
import { useMetricas } from "@/hooks/useMetricas"
import { StatTile } from "@/components/dashboard/StatTile"
import { Skeleton } from "@/components/ui/skeleton"

export function MetricsDashboard() {
  const { data: metricas, isLoading } = useMetricas()

  if (isLoading || !metricas) {
    return (
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-[74px]" />
        ))}
      </div>
    )
  }

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">
      <StatTile
        rotulo="Leads ativos"
        valor={metricas.total}
        icone={<Users className="size-4" />}
      />
      <StatTile
        rotulo="Contatados"
        valor={metricas.por_status.contatado ?? 0}
        icone={<CheckCircle2 className="size-4" />}
      />
      <StatTile
        rotulo="Responderam"
        valor={metricas.por_status.respondeu ?? 0}
        icone={<MessageCircle className="size-4" />}
      />
      <StatTile
        rotulo="Fechados"
        valor={metricas.por_status.fechou ?? 0}
        variante="destaque"
        icone={<Handshake className="size-4" />}
      />
      <StatTile
        rotulo="Conversão"
        valor={`${metricas.taxa_conversao}%`}
        variante="destaque"
        icone={<Percent className="size-4" />}
      />
      <StatTile
        rotulo="Follow-ups"
        valor={metricas.lembretes_hoje ?? 0}
        variante={(metricas.lembretes_hoje ?? 0) > 0 ? "alerta" : "default"}
        icone={<Clock className="size-4" />}
      />
    </div>
  )
}
