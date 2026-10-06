import { useEffect, useState } from "react"
import { Loader2, PlayCircle, Sparkles, TriangleAlert } from "lucide-react"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { EmptyStateCard } from "@/components/shared/EmptyStateCard"
import { SiteStatusBadge } from "@/components/leads/SiteStatusBadge"
import { usePreviaCampanha, useCriarCampanha } from "@/hooks/useCampanhas"
import { templateTemLink, templateTemMarcador } from "@/lib/presetsCampanha"
import type { CriarCampanhaInput, FiltrosCampanha, RitmoCampanha } from "@/types/whatsapp"

interface PreviaCampanhaPainelProps {
  filtros: FiltrosCampanha
  template: string
  limite: number
  ritmo: RitmoCampanha
  checarWhatsapp: boolean
  conectado: boolean
}

function estimarDuracaoMin(total: number, ritmo: RitmoCampanha): number {
  const intervaloMedioS = (ritmo.intervalo_min_s + ritmo.intervalo_max_s) / 2
  const pausas = ritmo.pausa_a_cada > 0 ? Math.floor(total / ritmo.pausa_a_cada) : 0
  const segundos = total * intervaloMedioS + pausas * ritmo.pausa_s
  return Math.round(segundos / 60)
}

function formatarDuracao(minutos: number): string {
  if (minutos < 1) return "menos de 1 min"
  if (minutos < 60) return `${minutos} min`
  const horas = Math.floor(minutos / 60)
  const resto = minutos % 60
  return resto > 0 ? `${horas}h${resto}min` : `${horas}h`
}

export function PreviaCampanhaPainel({
  filtros,
  template,
  limite,
  ritmo,
  checarWhatsapp,
  conectado,
}: PreviaCampanhaPainelProps) {
  const [nome, setNome] = useState("")
  const [debounced, setDebounced] = useState({ filtros, template, limite })

  // dá um respiro antes de bater no /previa a cada tecla digitada
  useEffect(() => {
    const timer = setTimeout(() => setDebounced({ filtros, template, limite }), 500)
    return () => clearTimeout(timer)
  }, [filtros, template, limite])

  const habilitado = template.trim().length > 0
  const previa = usePreviaCampanha(
    debounced.filtros,
    debounced.template,
    debounced.limite,
    habilitado
  )
  const criar = useCriarCampanha()

  const dados = previa.data
  const temLink = templateTemLink(template)
  const temMarcador = templateTemMarcador(template)
  const podeIniciar =
    conectado && habilitado && !temLink && !temMarcador && (dados?.total ?? 0) > 0

  const handleIniciar = () => {
    const input: CriarCampanhaInput = {
      nome: nome.trim() || undefined,
      filtros,
      template,
      limite,
      ritmo,
      checar_whatsapp: checarWhatsapp,
    }
    criar.mutate(input)
  }

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-border bg-card p-4">
        <Label>Nome da campanha (opcional)</Label>
        <Input
          value={nome}
          onChange={(e) => setNome(e.target.value)}
          placeholder="Ex: Clínicas Curitiba - semana 1"
          className="mt-1.5"
        />
      </div>

      <div className="space-y-3 rounded-xl border border-border bg-card p-4">
        <div className="flex items-center justify-between gap-2">
          <h3 className="font-medium">Prévia</h3>
          {previa.isFetching && (
            <Loader2 className="size-4 animate-spin text-muted-foreground" />
          )}
        </div>

        {!habilitado ? (
          <EmptyStateCard
            icone={<Sparkles className="size-5" />}
            titulo="Escreva a mensagem pra ver a prévia"
          />
        ) : previa.isLoading ? (
          <p className="text-sm text-muted-foreground">Calculando...</p>
        ) : dados ? (
          <>
            <div className="grid grid-cols-2 gap-2 text-center">
              <div className="rounded-lg bg-muted/40 p-2">
                <p className="text-xl font-semibold tabular-nums">{dados.total}</p>
                <p className="text-xs text-muted-foreground">na campanha</p>
              </div>
              <div className="rounded-lg bg-muted/40 p-2">
                <p className="text-xl font-semibold tabular-nums text-success">
                  {dados.teto_restante}
                </p>
                <p className="text-xs text-muted-foreground">restam no teto hoje</p>
              </div>
            </div>

            {Object.keys(dados.descartados).length > 0 && (
              <div className="space-y-1">
                <p className="text-xs font-medium text-muted-foreground">Descartados</p>
                <div className="flex flex-wrap gap-1.5">
                  {Object.entries(dados.descartados).map(([motivo, n]) => (
                    <Badge key={motivo} variant="outline">
                      {motivo}: {n}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {dados.aviso && (
              <p className="flex items-center gap-1.5 rounded-lg bg-warning/10 p-2 text-xs text-warning">
                <TriangleAlert className="size-3.5 shrink-0" />
                {dados.aviso}
              </p>
            )}

            {dados.leads.length > 0 && (
              <div className="max-h-64 space-y-1.5 overflow-y-auto">
                {dados.leads.slice(0, 8).map((lead) => (
                  <div
                    key={lead.place_id}
                    className="rounded-lg border border-border p-2 text-xs"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate font-medium">{lead.nome}</span>
                      <SiteStatusBadge siteStatus={lead.site_status} siteProblemas={null} />
                    </div>
                    <p className="mt-1 line-clamp-2 text-muted-foreground">
                      {lead.texto_exemplo}
                    </p>
                  </div>
                ))}
                {dados.leads.length > 8 && (
                  <p className="text-center text-xs text-muted-foreground">
                    + {dados.leads.length - 8} lead(s)
                  </p>
                )}
              </div>
            )}
          </>
        ) : null}

        {!conectado && (
          <p className="text-xs text-muted-foreground">
            Conecte o WhatsApp na página WhatsApp para poder iniciar a campanha.
          </p>
        )}

        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button className="w-full" disabled={!podeIniciar || criar.isPending}>
              <PlayCircle className="size-4" />
              Iniciar campanha
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Disparar para {dados?.total ?? 0} lead(s)?</AlertDialogTitle>
              <AlertDialogDescription>
                No ritmo configurado, a campanha deve levar cerca de{" "}
                {formatarDuracao(estimarDuracaoMin(dados?.total ?? 0, ritmo))} pra
                terminar, respeitando a janela de horário e o teto diário do chip.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancelar</AlertDialogCancel>
              <AlertDialogAction onClick={handleIniciar}>
                Disparar campanha
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </div>
  )
}
