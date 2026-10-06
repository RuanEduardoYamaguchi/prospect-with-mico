import { useEffect, useRef, useState } from "react"
import { ArrowLeft, Download, Search, Upload } from "lucide-react"
import { Link } from "react-router-dom"
import { Header } from "@/components/layout/Header"
import { Button } from "@/components/ui/button"
import { LeadFilterBar } from "@/components/filters/LeadFilterBar"
import { LeadGrid } from "@/components/leads/LeadGrid"
import { LeadDetailModal } from "@/components/lead-detail/LeadDetailModal"
import { ImportarKaptarDialog } from "@/components/leads/ImportarKaptarDialog"
import { NovaBuscaModal } from "@/components/search-modal/NovaBuscaModal"
import { HistoricoBuscas } from "@/components/search-modal/HistoricoBuscas"
import { BuscaFloatingIndicator } from "@/components/search-modal/BuscaFloatingIndicator"
import { useFiltrosLeads } from "@/hooks/useFiltrosLeads"
import { useBusca } from "@/hooks/useBusca"
import { useLeads } from "@/hooks/useLeads"
import { useAtalhosTeclado } from "@/hooks/useAtalhosTeclado"
import { urlExportarCsv } from "@/services/leadsService"
import type { Lead } from "@/types/lead"

export function LeadsMapsPage() {
  const { filtros, setFiltros, limpar, filtrosEmUso } = useFiltrosLeads()
  const buscaInputRef = useRef<HTMLInputElement>(null)
  const [placeIdSelecionado, setPlaceIdSelecionado] = useState<string | null>(
    null
  )
  const { leads } = useLeads(filtros)
  // guarda o lead do modal em estado próprio: se ele sair da lista (ex.: mudei o
  // status pra um que não passa no filtro atual), o modal continua aberto com o
  // último dado conhecido em vez de fechar sozinho no meio da interação.
  const [leadSelecionado, setLeadSelecionado] = useState<Lead | null>(null)
  useEffect(() => {
    if (placeIdSelecionado === null) {
      setLeadSelecionado(null)
      return
    }
    const atual = leads.find((l) => l.place_id === placeIdSelecionado)
    if (atual) setLeadSelecionado(atual) // atualiza enquanto o lead está visível
  }, [placeIdSelecionado, leads])
  const [modalBuscaAberto, setModalBuscaAberto] = useState(false)
  const [buscaMinimizada, setBuscaMinimizada] = useState(false)
  const [modalImportarAberto, setModalImportarAberto] = useState(false)
  const busca = useBusca()
  const { resultadoFinal } = busca

  useEffect(() => {
    if (resultadoFinal && buscaMinimizada) {
      setBuscaMinimizada(false)
      setModalBuscaAberto(true)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resultadoFinal])

  useAtalhosTeclado({
    onFocarBusca: () => buscaInputRef.current?.focus(),
    onNovaBusca: () => setModalBuscaAberto(true),
  })

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Header onNovaBusca={() => setModalBuscaAberto(true)} />

      <main className="mx-auto w-full max-w-6xl space-y-6 px-4 py-6 sm:px-6">
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-4" />
          Voltar para o dashboard
        </Link>

        <h1 className="text-xl font-semibold">Leads do Google Maps</h1>

        <HistoricoBuscas />

        <div className="flex flex-wrap items-center justify-between gap-2">
          <LeadFilterBar
            filtros={filtros}
            setFiltros={setFiltros}
            filtrosEmUso={filtrosEmUso}
            onLimpar={limpar}
            buscaInputRef={buscaInputRef}
          />
          <div className="flex flex-wrap items-center gap-2">
            <Button size="sm" onClick={() => setModalBuscaAberto(true)}>
              <Search className="size-4" />
              Nova busca
            </Button>
            <Button variant="outline" size="sm" onClick={() => setModalImportarAberto(true)}>
              <Upload className="size-4" />
              <span className="hidden sm:inline">Importar CSV do Kaptar</span>
            </Button>
            <Button variant="outline" size="sm" asChild>
              <a href={urlExportarCsv(filtros)}>
                <Download className="size-4" />
                <span className="hidden sm:inline">Exportar CSV</span>
              </a>
            </Button>
          </div>
        </div>

        <LeadGrid
          filtros={filtros}
          filtrosEmUso={filtrosEmUso}
          onLimparFiltros={limpar}
          onSelecionarLead={(lead) => setPlaceIdSelecionado(lead.place_id)}
          onNovaBusca={() => setModalBuscaAberto(true)}
        />
      </main>

      <LeadDetailModal
        lead={leadSelecionado}
        onClose={() => setPlaceIdSelecionado(null)}
      />

      <NovaBuscaModal
        aberto={modalBuscaAberto && !buscaMinimizada}
        onFechar={() => setModalBuscaAberto(false)}
        onMinimizar={() => setBuscaMinimizada(true)}
        busca={busca}
      />

      <ImportarKaptarDialog
        aberto={modalImportarAberto}
        onFechar={() => setModalImportarAberto(false)}
      />

      {buscaMinimizada && busca.statusBusca.data && (
        <BuscaFloatingIndicator
          mensagem={busca.statusBusca.data.mensagem}
          onClick={() => setBuscaMinimizada(false)}
        />
      )}
    </div>
  )
}
