import { useState } from "react"
import { ArrowLeft, Send } from "lucide-react"
import { Link } from "react-router-dom"
import { Header } from "@/components/layout/Header"
import { PageHero } from "@/components/shared/PageHero"
import { Skeleton } from "@/components/ui/skeleton"
import { FiltrosCampanhaForm } from "@/components/campanhas/FiltrosCampanhaForm"
import { TemplateCampanhaForm } from "@/components/campanhas/TemplateCampanhaForm"
import { RitmoCampanhaForm } from "@/components/campanhas/RitmoCampanhaForm"
import { PreviaCampanhaPainel } from "@/components/campanhas/PreviaCampanhaPainel"
import { CampanhaAtivaPainel } from "@/components/campanhas/CampanhaAtivaPainel"
import { HistoricoCampanhasTable } from "@/components/campanhas/HistoricoCampanhasTable"
import { AvisoNumeroOficial } from "@/components/whatsapp/AvisoNumeroOficial"
import { useCampanhas } from "@/hooks/useCampanhas"
import { useEstadoWhatsapp } from "@/hooks/useWhatsapp"
import { FILTROS_CAMPANHA_PADRAO, RITMO_CAMPANHA_PADRAO } from "@/types/whatsapp"

export function CampanhasPage() {
  const [filtros, setFiltros] = useState(FILTROS_CAMPANHA_PADRAO)
  const [template, setTemplate] = useState("")
  const [limite, setLimite] = useState(30)
  const [ritmo, setRitmo] = useState(RITMO_CAMPANHA_PADRAO)
  const [checarWhatsapp, setCheckarWhatsapp] = useState(true)

  const { data: estado } = useEstadoWhatsapp()
  const campanhas = useCampanhas()

  const campanhaAtiva = campanhas.data?.ativa ?? null
  const emAndamento = campanhaAtiva !== null

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Header />

      <main className="mx-auto w-full max-w-6xl space-y-6 px-4 py-6 sm:px-6">
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-4" />
          Voltar para o dashboard
        </Link>

        <PageHero
          icone={<Send className="size-6" />}
          titulo="Campanhas de WhatsApp"
          descricao="Disparo em massa pro miolo do funil (score 40 a 69) - filtro, ritmo e prévia antes de sair mandando."
          gradiente="from-success/80 via-success/70 to-success/85"
        />

        {estado?.conectado && estado.numero_oficial && <AvisoNumeroOficial />}
        {estado?.conectado && estado.oficial_liberado && <AvisoNumeroOficial liberado />}

        {campanhas.isLoading ? (
          <Skeleton className="h-[320px] rounded-xl" />
        ) : emAndamento && campanhaAtiva ? (
          <CampanhaAtivaPainel campanha={campanhaAtiva} />
        ) : (
          <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
            <div className="space-y-4">
              <FiltrosCampanhaForm
                filtros={filtros}
                onChange={setFiltros}
                limite={limite}
                onChangeLimite={setLimite}
              />
              <TemplateCampanhaForm template={template} onChange={setTemplate} />
              <RitmoCampanhaForm
                ritmo={ritmo}
                onChange={setRitmo}
                checarWhatsapp={checarWhatsapp}
                onChangeCheckarWhatsapp={setCheckarWhatsapp}
              />
            </div>

            <PreviaCampanhaPainel
              filtros={filtros}
              template={template}
              limite={limite}
              ritmo={ritmo}
              checarWhatsapp={checarWhatsapp}
              conectado={Boolean(estado?.conectado && !estado.numero_oficial)}
            />
          </div>
        )}

        <div className="space-y-2">
          <h2 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Histórico
          </h2>
          <HistoricoCampanhasTable historico={campanhas.data?.historico ?? []} />
        </div>
      </main>
    </div>
  )
}
