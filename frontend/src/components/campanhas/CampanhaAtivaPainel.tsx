import { useEffect, useState } from "react"
import { Loader2, Pause, Play, Trash2, TriangleAlert } from "lucide-react"
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
import { cn } from "@/lib/utils"
import { COR_STATUS_CAMPANHA, LABEL_STATUS_CAMPANHA } from "@/lib/constants"
import { useCampanhaMutations } from "@/hooks/useCampanhas"
import type { Campanha } from "@/types/whatsapp"

interface CampanhaAtivaPainelProps {
  campanha: Campanha
}

/** Relógio local que só serve pra recalcular a contagem regressiva a cada
 * segundo - a campanha em si já vem atualizada pelo polling do useCampanhas. */
function useAgora() {
  const [agora, setAgora] = useState(() => Date.now())
  useEffect(() => {
    const id = setInterval(() => setAgora(Date.now()), 1000)
    return () => clearInterval(id)
  }, [])
  return agora
}

function formatarContagem(alvoIso: string, agora: number): string {
  const diff = new Date(alvoIso).getTime() - agora
  if (diff <= 0) return "a qualquer momento"
  const segundos = Math.floor(diff / 1000)
  const min = Math.floor(segundos / 60)
  const seg = segundos % 60
  return min > 0 ? `${min}min ${seg}s` : `${seg}s`
}

const COR_STATUS_ENVIO: Record<string, string> = {
  enviado: "border-success/30 bg-success/15 text-success",
  falhou: "border-destructive/30 bg-destructive/15 text-destructive",
  pulado: "border-border bg-muted text-muted-foreground",
}

export function CampanhaAtivaPainel({ campanha }: CampanhaAtivaPainelProps) {
  const { parar, retomar, descartar } = useCampanhaMutations(campanha.id)
  const agora = useAgora()
  const processados = campanha.enviados + campanha.falhas + campanha.pulados
  const percentual =
    campanha.total > 0 ? Math.round((processados / campanha.total) * 100) : 0

  return (
    <div className="space-y-4">
      {campanha.status === "interrompida" && (
        <div className="space-y-2 rounded-xl border border-warning/40 bg-warning/10 p-4">
          <div className="flex items-center gap-2">
            <TriangleAlert className="size-4 text-warning" />
            <h3 className="font-medium">Campanha interrompida</h3>
          </div>
          <p className="text-sm text-muted-foreground">
            {campanha.ultimo_erro ??
              "O backend reiniciou no meio do disparo - nada foi perdido."}{" "}
            Retome de onde parou ou descarte o que falta.
          </p>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" onClick={() => retomar.mutate()} disabled={retomar.isPending}>
              <Play className="size-4" />
              Retomar de onde parou
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => descartar.mutate()}
              disabled={descartar.isPending}
            >
              Descartar
            </Button>
          </div>
        </div>
      )}

      <div className="space-y-3 rounded-xl border border-border bg-card p-4">
        <div className="flex items-center justify-between gap-2">
          <h3 className="font-medium">{campanha.nome}</h3>
          <Badge variant="outline" className={COR_STATUS_CAMPANHA[campanha.status]}>
            {LABEL_STATUS_CAMPANHA[campanha.status]}
          </Badge>
        </div>

        <div className="grid grid-cols-4 gap-2 text-center">
          <div className="rounded-lg bg-muted/40 p-2">
            <p className="text-lg font-semibold tabular-nums text-success">
              {campanha.enviados}
            </p>
            <p className="text-xs text-muted-foreground">enviados</p>
          </div>
          <div className="rounded-lg bg-muted/40 p-2">
            <p className="text-lg font-semibold tabular-nums text-destructive">
              {campanha.falhas}
            </p>
            <p className="text-xs text-muted-foreground">falhas</p>
          </div>
          <div className="rounded-lg bg-muted/40 p-2">
            <p className="text-lg font-semibold tabular-nums">{campanha.pulados}</p>
            <p className="text-xs text-muted-foreground">pulados</p>
          </div>
          <div className="rounded-lg bg-muted/40 p-2">
            <p className="text-lg font-semibold tabular-nums">{campanha.total}</p>
            <p className="text-xs text-muted-foreground">total</p>
          </div>
        </div>

        <div className="h-2 overflow-hidden rounded-full bg-border">
          <div
            className="h-full rounded-full bg-primary transition-all"
            style={{ width: `${percentual}%` }}
          />
        </div>

        {campanha.status === "rodando" && (
          <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
            <Loader2 className="size-3.5 shrink-0 animate-spin" />
            {campanha.aguardando_janela
              ? "Fora da janela de horário - aguardando reabrir, sem parar a campanha"
              : campanha.proximo_envio_em
                ? `Próximo envio em ${formatarContagem(campanha.proximo_envio_em, agora)}`
                : "Enviando..."}
          </p>
        )}

        {campanha.ultimo_erro && campanha.status !== "interrompida" && (
          <p className="flex items-center gap-1.5 text-xs text-destructive">
            <TriangleAlert className="size-3.5 shrink-0" />
            {campanha.ultimo_erro}
          </p>
        )}

        {campanha.ultimos.length > 0 && (
          <div className="space-y-1">
            <p className="text-xs font-medium text-muted-foreground">Últimos envios</p>
            <div className="max-h-48 space-y-1 overflow-y-auto">
              {campanha.ultimos.map((envio, i) => (
                <div
                  key={`${envio.telefone}-${i}`}
                  className="flex items-center justify-between gap-2 rounded-lg border border-border px-2 py-1 text-xs"
                >
                  <span className="truncate">{envio.nome}</span>
                  <Badge
                    variant="outline"
                    className={cn(COR_STATUS_ENVIO[envio.status])}
                  >
                    {envio.status}
                  </Badge>
                </div>
              ))}
            </div>
          </div>
        )}

        {(campanha.status === "rodando" || campanha.status === "pausada") && (
          <div className="flex flex-wrap gap-2 border-t border-border pt-3">
            {campanha.status === "rodando" ? (
              <Button
                size="sm"
                variant="outline"
                onClick={() => parar.mutate()}
                disabled={parar.isPending}
              >
                <Pause className="size-4" />
                Parar
              </Button>
            ) : (
              <Button size="sm" onClick={() => retomar.mutate()} disabled={retomar.isPending}>
                <Play className="size-4" />
                Retomar
              </Button>
            )}

            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button
                  size="sm"
                  variant="outline"
                  className="text-destructive hover:bg-destructive/10"
                >
                  <Trash2 className="size-4" />
                  Descartar
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Descartar esta campanha?</AlertDialogTitle>
                  <AlertDialogDescription>
                    Os envios pendentes viram "pulado" e não saem mais. Os já
                    enviados continuam valendo no histórico.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancelar</AlertDialogCancel>
                  <AlertDialogAction onClick={() => descartar.mutate()}>
                    Descartar
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        )}
      </div>
    </div>
  )
}
