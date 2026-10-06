import { Link } from "react-router-dom"
import { ArrowRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Header } from "@/components/layout/Header"
import { MetricsDashboard } from "@/components/dashboard/MetricsDashboard"
import { PrimeirosPassosCard } from "@/components/onboarding/PrimeirosPassosCard"
import { FunilConversao } from "@/components/dashboard/FunilConversao"
import { BreakdownNicho } from "@/components/dashboard/BreakdownNicho"
import { useTarefasHoje } from "@/hooks/useTarefasHoje"
import { useLeads } from "@/hooks/useLeads"
import { FILTROS_VAZIOS } from "@/types/lead"

const FILTROS_NOVOS = { ...FILTROS_VAZIOS, status: "novo" as const, ordenar: "score" as const }

export function DashboardPage() {
  const { tarefas } = useTarefasHoje()
  const followups = (tarefas.data?.followups ?? []).filter((t) => t.canal === "maps").length
  const filaNovos = useLeads(FILTROS_NOVOS)
  const novos = filaNovos.leads.length
  const novosTexto = `${novos}${filaNovos.hasNextPage ? "+" : ""}`
  const carregando = tarefas.isLoading || filaNovos.isLoading

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Header />

      <main className="mx-auto w-full max-w-6xl space-y-6 px-4 py-6 sm:px-6">
        <PrimeirosPassosCard />

        <section className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-border bg-card p-5 shadow-sm">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-primary">Próximo passo</p>
            <p className="mt-1 text-lg font-semibold tracking-tight">
              {carregando
                ? "Carregando..."
                : followups + novos === 0
                  ? "Nada vencendo hoje."
                  : `${followups} follow-up(s) vencido(s) e ${novosTexto} lead(s) novo(s) na fila.`}
            </p>
          </div>
          <Button asChild>
            <Link to="/hoje">
              Começar o dia
              <ArrowRight className="size-4" />
            </Link>
          </Button>
        </section>

        <MetricsDashboard />

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <FunilConversao />
          <BreakdownNicho />
        </div>
      </main>
    </div>
  )
}
