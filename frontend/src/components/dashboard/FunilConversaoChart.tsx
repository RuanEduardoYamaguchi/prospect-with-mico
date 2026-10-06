import {
  Bar,
  BarChart,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { Filter } from "lucide-react"
import { LABEL_STATUS } from "@/lib/constants"
import { Skeleton } from "@/components/ui/skeleton"
import { EmptyStateCard } from "@/components/shared/EmptyStateCard"
import type { EstagioFunil } from "@/types/analytics"

// rampa sequencial da marca: o funil é uma progressão ordenada (novo → fechou),
// então a cor codifica o avanço no mesmo matiz, do claro ao escuro - nunca
// quatro matizes soltos
const CORES_ESTAGIO = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
]

interface FunilConversaoChartProps {
  estagios: EstagioFunil[] | undefined
  isLoading: boolean
}

export function FunilConversaoChart({
  estagios,
  isLoading,
}: FunilConversaoChartProps) {
  if (isLoading || !estagios) {
    return <Skeleton className="h-[280px]" />
  }

  const dados = estagios.map((e) => ({
    estagio: LABEL_STATUS[e.status],
    total: e.total,
  }))
  const vazio = dados.every((d) => d.total === 0)

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <h3 className="mb-4 text-sm font-medium text-muted-foreground">
        Funil de conversão
      </h3>
      {vazio ? (
        <EmptyStateCard
          icone={<Filter className="size-5" />}
          titulo="Funil ainda vazio"
          descricao="Quando você tiver leads e for movendo eles pelo funil (contatado, respondeu, fechou), o gráfico aparece aqui."
          className="h-[240px] border-0 bg-transparent"
        />
      ) : (
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={dados} layout="vertical" margin={{ left: 12, right: 32 }}>
            <XAxis type="number" allowDecimals={false} hide />
            <YAxis
              type="category"
              dataKey="estagio"
              width={90}
              axisLine={false}
              tickLine={false}
              tick={{ fill: "var(--muted-foreground)", fontSize: 12 }}
            />
            <Tooltip
              cursor={{ fill: "var(--muted)", opacity: 0.5 }}
              contentStyle={{
                background: "var(--popover)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                color: "var(--popover-foreground)",
              }}
            />
            <Bar dataKey="total" barSize={22} radius={[0, 4, 4, 0]}>
              {dados.map((_, i) => (
                <Cell key={i} fill={CORES_ESTAGIO[i % CORES_ESTAGIO.length]} />
              ))}
              <LabelList
                dataKey="total"
                position="right"
                style={{ fill: "var(--muted-foreground)", fontSize: 12 }}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
