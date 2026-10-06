import { Fragment, useEffect, useRef, useState } from "react"
import L from "leaflet"
import "leaflet/dist/leaflet.css"
import {
  Circle,
  MapContainer,
  Marker,
  TileLayer,
  useMap,
  useMapEvents,
} from "react-leaflet"
import { MapPin, Search, X } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import type { AreaBusca } from "@/types/busca"

const MAX_AREAS = 5
const RAIO_PADRAO_M = 5000
const RAIO_MIN_M = 500
const RAIO_MAX_M = 50000
const CENTRO_BRASIL: [number, number] = [-15.78, -47.93]

// cores fixas (o SVG do Leaflet não resolve var() do CSS)
const COR_AREA = "#059669"
const COR_AREA_PREENCHIMENTO = "#10b981"

function iconePino(numero: number) {
  return L.divIcon({
    className: "",
    html: `<div class="flex size-7 items-center justify-center rounded-full border-2 border-white bg-emerald-600 text-xs font-bold text-white shadow-lg">${numero}</div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  })
}

/** Nome amigável do lugar sob o pino ("Londrina - Paraná") via Nominatim/OSM.
 * Best-effort: falha vira null e o rótulo cai nas coordenadas. */
async function geocodificarReverso(lat: number, lng: number): Promise<string | null> {
  try {
    const resposta = await fetch(
      `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lng}&zoom=12&accept-language=pt-BR`
    )
    if (!resposta.ok) return null
    const dados = await resposta.json()
    const endereco = dados.address ?? {}
    const cidade =
      endereco.city || endereco.town || endereco.village || endereco.municipality || dados.name
    if (!cidade) return null
    return endereco.state ? `${cidade} - ${endereco.state}` : cidade
  } catch {
    return null
  }
}

interface ResultadoLocal {
  label: string
  lat: number
  lng: number
}

async function buscarLocais(consulta: string): Promise<ResultadoLocal[]> {
  const resposta = await fetch(
    `https://nominatim.openstreetmap.org/search?format=jsonv2&q=${encodeURIComponent(consulta)}&countrycodes=br&limit=5&accept-language=pt-BR`
  )
  if (!resposta.ok) return []
  const dados: { display_name: string; lat: string; lon: string }[] = await resposta.json()
  return dados.map((d) => ({
    label: d.display_name,
    lat: Number(d.lat),
    lng: Number(d.lon),
  }))
}

function CapturadorDeCliques({ onClique }: { onClique: (lat: number, lng: number) => void }) {
  useMapEvents({
    click: (evento) => onClique(evento.latlng.lat, evento.latlng.lng),
  })
  return null
}

function VoarPara({ destino }: { destino: [number, number] | null }) {
  const mapa = useMap()
  useEffect(() => {
    if (destino) {
      mapa.flyTo(destino, 12, { duration: 0.8 })
    }
  }, [destino, mapa])
  return null
}

/** O Leaflet mede o container só uma vez, na montagem - dentro de um modal
 * animado (zoom/fade) a medida sai errada e o mapa fica com faixas cinzas sem
 * tiles. Recalcula depois da animação e sempre que o container mudar de tamanho. */
function AjustarTamanhoDoMapa() {
  const mapa = useMap()
  useEffect(() => {
    const timer = setTimeout(() => mapa.invalidateSize(), 200)
    const observador = new ResizeObserver(() => mapa.invalidateSize())
    observador.observe(mapa.getContainer())
    return () => {
      clearTimeout(timer)
      observador.disconnect()
    }
  }, [mapa])
  return null
}

function formatarRaio(raioM: number): string {
  return raioM < 1000 ? `${raioM} m` : `${(raioM / 1000).toLocaleString("pt-BR")} km`
}

interface MapaSeletorAreasProps {
  areas: AreaBusca[]
  onChange: (areas: AreaBusca[]) => void
  desabilitado?: boolean
}

export function MapaSeletorAreas({
  areas,
  onChange,
  desabilitado = false,
}: MapaSeletorAreasProps) {
  const [consultaLocal, setConsultaLocal] = useState("")
  const [resultadosLocal, setResultadosLocal] = useState<ResultadoLocal[]>([])
  const [buscandoLocal, setBuscandoLocal] = useState(false)
  const [destinoVoo, setDestinoVoo] = useState<[number, number] | null>(null)
  const proximoId = useRef(1)

  const adicionarArea = async (lat: number, lng: number) => {
    if (desabilitado) return
    if (areas.length >= MAX_AREAS) {
      toast.warning(`Máximo de ${MAX_AREAS} áreas por busca.`)
      return
    }
    const id = String(proximoId.current++)
    const nova: AreaBusca = {
      id,
      lat,
      lng,
      raio_m: RAIO_PADRAO_M,
      rotulo: `${lat.toFixed(4)}, ${lng.toFixed(4)}`,
    }
    onChange([...areas, nova])

    const rotulo = await geocodificarReverso(lat, lng)
    if (rotulo) {
      atualizarArea(id, { rotulo }, [...areas, nova])
    }
  }

  const atualizarArea = (
    id: string,
    mudancas: Partial<AreaBusca>,
    base: AreaBusca[] = areas
  ) => {
    onChange(base.map((a) => (a.id === id ? { ...a, ...mudancas } : a)))
  }

  const moverArea = async (id: string, lat: number, lng: number) => {
    atualizarArea(id, { lat, lng })
    const rotulo = await geocodificarReverso(lat, lng)
    if (rotulo) {
      atualizarArea(id, { lat, lng, rotulo })
    }
  }

  const removerArea = (id: string) => {
    onChange(areas.filter((a) => a.id !== id))
  }

  const handleBuscarLocal = async () => {
    const consulta = consultaLocal.trim()
    if (!consulta) return
    setBuscandoLocal(true)
    try {
      const resultados = await buscarLocais(consulta)
      setResultadosLocal(resultados)
      if (resultados.length === 0) toast.info("Nenhum lugar encontrado com esse nome.")
    } finally {
      setBuscandoLocal(false)
    }
  }

  const irParaLocal = (local: ResultadoLocal) => {
    setDestinoVoo([local.lat, local.lng])
    setResultadosLocal([])
    setConsultaLocal("")
    // zera o destino no próximo tick pra permitir voar de novo pro mesmo lugar
    setTimeout(() => setDestinoVoo(null), 1000)
  }

  return (
    <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_320px]">
      {/* Coluna do mapa - ocupa o máximo de largura disponível */}
      <div className="relative isolate z-0 h-[340px] overflow-hidden rounded-xl border border-border lg:h-[520px]">
        <MapContainer
          center={CENTRO_BRASIL}
          zoom={4}
          className="size-full"
          scrollWheelZoom
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <AjustarTamanhoDoMapa />
          <CapturadorDeCliques onClique={adicionarArea} />
          <VoarPara destino={destinoVoo} />
          {areas.map((area, indice) => (
            <Fragment key={area.id}>
              <Marker
                position={[area.lat, area.lng]}
                icon={iconePino(indice + 1)}
                draggable={!desabilitado}
                eventHandlers={{
                  dragend: (evento) => {
                    const posicao = (evento.target as L.Marker).getLatLng()
                    moverArea(area.id, posicao.lat, posicao.lng)
                  },
                }}
              />
              <Circle
                center={[area.lat, area.lng]}
                radius={area.raio_m}
                pathOptions={{
                  color: COR_AREA,
                  fillColor: COR_AREA_PREENCHIMENTO,
                  fillOpacity: 0.12,
                  weight: 2,
                }}
              />
            </Fragment>
          ))}
        </MapContainer>
        {areas.length === 0 && (
          <div className="pointer-events-none absolute inset-x-0 bottom-2 z-[1000] flex justify-center">
            <span className="rounded-full bg-background/90 px-3 py-1 text-xs text-muted-foreground shadow-sm backdrop-blur">
              Clique no mapa para adicionar um pino de busca
            </span>
          </div>
        )}
      </div>

      {/* Painel lateral - busca de lugar, áreas e conteúdo extra (nichos) */}
      <div className="flex min-w-0 flex-col gap-3">
        <div className="relative">
          <div className="flex gap-2">
            <Input
              value={consultaLocal}
              onChange={(e) => setConsultaLocal(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault()
                  handleBuscarLocal()
                }
              }}
              placeholder="Buscar cidade ou bairro..."
              disabled={desabilitado}
            />
            <Button
              type="button"
              variant="outline"
              onClick={handleBuscarLocal}
              disabled={desabilitado || buscandoLocal}
              aria-label="Buscar lugar"
            >
              <Search className="size-4" />
            </Button>
          </div>
          {resultadosLocal.length > 0 && (
            <div className="absolute inset-x-0 top-full z-[1100] mt-1 overflow-hidden rounded-lg border border-border bg-popover shadow-md">
              {resultadosLocal.map((local) => (
                <button
                  key={`${local.lat}-${local.lng}`}
                  type="button"
                  onClick={() => irParaLocal(local)}
                  className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-accent"
                >
                  <MapPin className="size-3.5 shrink-0 text-muted-foreground" />
                  <span className="truncate">{local.label}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-0.5">
          {areas.length === 0 ? (
            <p className="rounded-lg border border-dashed border-border bg-muted/20 px-3 py-4 text-center text-xs text-muted-foreground">
              Nenhuma área ainda - clique no mapa para soltar o primeiro pino.
            </p>
          ) : (
            areas.map((area, indice) => (
              <div
                key={area.id}
                className="space-y-2 rounded-lg border border-border bg-muted/30 px-3 py-2"
              >
                <div className="flex items-center gap-2">
                  <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-emerald-600 text-[10px] font-bold text-white">
                    {indice + 1}
                  </span>
                  <Input
                    value={area.rotulo}
                    onChange={(e) => atualizarArea(area.id, { rotulo: e.target.value })}
                    disabled={desabilitado}
                    className="h-7 min-w-0 flex-1 text-sm"
                    aria-label={`Rótulo da área ${indice + 1}`}
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="size-7 shrink-0 p-0 text-muted-foreground hover:text-destructive"
                    onClick={() => removerArea(area.id)}
                    disabled={desabilitado}
                    aria-label={`Remover área ${indice + 1}`}
                  >
                    <X className="size-3.5" />
                  </Button>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="range"
                    min={RAIO_MIN_M}
                    max={RAIO_MAX_M}
                    step={500}
                    value={area.raio_m}
                    onChange={(e) => atualizarArea(area.id, { raio_m: Number(e.target.value) })}
                    disabled={desabilitado}
                    className="min-w-0 flex-1 accent-emerald-600"
                    aria-label={`Raio da área ${indice + 1}`}
                  />
                  <span className="w-16 shrink-0 text-right text-xs font-medium tabular-nums text-muted-foreground">
                    {formatarRaio(area.raio_m)}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
