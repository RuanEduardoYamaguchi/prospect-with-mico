import { useState } from "react"
import { Map, Type } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { BuscaProgress } from "@/components/search-modal/BuscaProgress"
import { BuscaResultado } from "@/components/search-modal/BuscaResultado"
import { MapaSeletorAreas } from "@/components/search-modal/MapaSeletorAreas"
import { SeletorNichos } from "@/components/search-modal/SeletorNichos"
import type { useBusca } from "@/hooks/useBusca"
import type { AreaBusca } from "@/types/busca"

type ModoBusca = "texto" | "mapa"

interface NovaBuscaModalProps {
  aberto: boolean
  onFechar: () => void
  onMinimizar: () => void
  busca: ReturnType<typeof useBusca>
}

export function NovaBuscaModal({
  aberto,
  onFechar,
  onMinimizar,
  busca,
}: NovaBuscaModalProps) {
  const [modo, setModo] = useState<ModoBusca>("texto")
  const [queries, setQueries] = useState("")
  const [nichos, setNichos] = useState<string[]>([])
  const [areas, setAreas] = useState<AreaBusca[]>([])
  const {
    dispararBusca,
    dispararBuscaMapa,
    statusBusca,
    pollingAtivo,
    resultadoFinal,
    limparResultado,
  } = busca

  const rodando = pollingAtivo && statusBusca.data?.rodando
  const disparando = dispararBusca.isPending || dispararBuscaMapa.isPending

  const podeBuscar =
    modo === "texto" ? Boolean(queries.trim()) : nichos.length > 0 && areas.length > 0

  const handleConfirmar = () => {
    if (!podeBuscar) return
    if (modo === "texto") {
      dispararBusca.mutate(queries)
    } else {
      dispararBuscaMapa.mutate({
        nichos,
        areas: areas.map(({ lat, lng, raio_m, rotulo }) => ({ lat, lng, raio_m, rotulo })),
      })
    }
  }

  const handleFechar = () => {
    limparResultado()
    onFechar()
  }

  return (
    <Dialog open={aberto} onOpenChange={(open) => !open && !rodando && handleFechar()}>
      <DialogContent
        className={cn(
          modo === "mapa" ? "sm:max-w-5xl" : "sm:max-w-lg",
          "max-h-[92vh] overflow-y-auto"
        )}
        onInteractOutside={(e) => rodando && e.preventDefault()}
        onEscapeKeyDown={(e) => rodando && e.preventDefault()}
      >
        <DialogHeader>
          <DialogTitle>Nova busca de leads</DialogTitle>
          <DialogDescription>
            {modo === "texto"
              ? 'Um nicho + cidade por linha, ex.: "clínica de estética em Londrina"'
              : "Solte pinos no mapa, ajuste o raio de cada um e diga quais nichos procurar."}
          </DialogDescription>
        </DialogHeader>

        <div className="flex gap-1 rounded-lg bg-muted p-1">
          <button
            type="button"
            onClick={() => setModo("texto")}
            disabled={Boolean(rodando)}
            className={cn(
              "flex flex-1 items-center justify-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
              modo === "texto"
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            <Type className="size-4" />
            Por texto
          </button>
          <button
            type="button"
            onClick={() => setModo("mapa")}
            disabled={Boolean(rodando)}
            className={cn(
              "flex flex-1 items-center justify-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
              modo === "mapa"
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            <Map className="size-4" />
            Por mapa
          </button>
        </div>

        {modo === "texto" ? (
          <Textarea
            rows={8}
            value={queries}
            onChange={(e) => setQueries(e.target.value)}
            disabled={Boolean(rodando)}
            placeholder={"clínica de estética em Londrina\ncorretor de imóveis em Londrina"}
          />
        ) : (
          <div className="space-y-4">
            <MapaSeletorAreas
              areas={areas}
              onChange={setAreas}
              desabilitado={Boolean(rodando)}
            />
            <SeletorNichos
              selecionados={nichos}
              onChange={setNichos}
              desabilitado={Boolean(rodando)}
            />
          </div>
        )}

        {statusBusca.data && pollingAtivo && (
          <BuscaProgress estado={statusBusca.data} />
        )}

        {resultadoFinal && <BuscaResultado estado={resultadoFinal} />}

        <div className="flex justify-end gap-2">
          {!rodando && (
            <Button variant="ghost" onClick={handleFechar}>
              {resultadoFinal ? "Fechar" : "Cancelar"}
            </Button>
          )}
          {rodando && (
            <Button variant="ghost" onClick={onMinimizar}>
              Minimizar e continuar usando
            </Button>
          )}
          <Button onClick={handleConfirmar} disabled={Boolean(rodando) || disparando || !podeBuscar}>
            {rodando || disparando
              ? "Buscando..."
              : modo === "mapa" && areas.length > 1
                ? `Buscar em ${areas.length} áreas`
                : "Buscar"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
