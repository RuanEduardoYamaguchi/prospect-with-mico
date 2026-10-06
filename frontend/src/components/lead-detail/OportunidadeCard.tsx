import { useState } from "react"
import { AlertTriangle, ChevronDown, Lightbulb } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useAnalisarOportunidade, useOportunidade } from "@/hooks/useMicrodemo"
import { cn } from "@/lib/utils"
import {
  COR_CONFIANCA,
  COR_RECOMENDACAO,
  LABEL_CONFIANCA,
  LABEL_MICRO_DEMO,
  LABEL_RECOMENDACAO,
} from "@/types/microdemo"

const TITULO_SECAO = "text-xs font-semibold uppercase tracking-wider text-muted-foreground"

function formatarData(iso: string) {
  const data = new Date(iso)
  if (Number.isNaN(data.getTime())) return iso
  return data.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" })
}

function Secao({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <div>
      <h4 className={TITULO_SECAO}>{titulo}</h4>
      <div className="mt-1.5 text-sm leading-relaxed">{children}</div>
    </div>
  )
}

export function OportunidadeCard({ placeId }: { placeId: string }) {
  const [aberta, setAberta] = useState(false)
  const { data, isLoading } = useOportunidade(placeId, { enabled: aberta })
  const analisar = useAnalisarOportunidade(placeId)

  const analise = data?.analise ?? null
  const abaixoDoMinimo = data ? data.score < data.score_min : false

  return (
    <div className="flex flex-col gap-4 rounded-xl border border-border bg-card p-4">
      <button
        type="button"
        onClick={() => setAberta((v) => !v)}
        aria-expanded={aberta}
        className="flex items-center gap-2 text-left font-semibold"
      >
        <Lightbulb className="size-4 text-success" />
        Oportunidade comercial
        <ChevronDown
          className={cn("ml-auto size-4 text-muted-foreground transition-transform", aberta && "rotate-180")}
        />
      </button>

      {!aberta ? null : isLoading || !data ? (
        <Skeleton className="h-9 w-full" />
      ) : (
        <div className="flex flex-col gap-1.5">
          <Button
            variant={analise ? "outline" : "default"}
            onClick={() => analisar.mutate()}
            disabled={analisar.isPending || abaixoDoMinimo}
            className="w-full"
          >
            <Lightbulb className="size-4" />
            {analisar.isPending
              ? "Analisando..."
              : analise
                ? "Refazer análise"
                : "Analisar oportunidade"}
          </Button>
          {abaixoDoMinimo && (
            <p className="text-xs text-muted-foreground">
              score {data.score}, mínimo {data.score_min} para análise
            </p>
          )}
        </div>
      )}

      {aberta && analise && (
        <div className="flex flex-col gap-4">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={cn(
                "rounded-full px-2.5 py-0.5 text-xs font-medium",
                COR_RECOMENDACAO[analise.recomendacao]
              )}
            >
              {LABEL_RECOMENDACAO[analise.recomendacao]}
            </span>
            <span
              className={cn(
                "rounded-full px-2.5 py-0.5 text-xs font-medium",
                COR_CONFIANCA[analise.confianca]
              )}
            >
              {LABEL_CONFIANCA[analise.confianca]}
            </span>
          </div>

          {analise.motivo_nao_abordar && (
            <div className="rounded-lg border-l-2 border-warning bg-warning/10 p-3">
              <h4 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-warning">
                <AlertTriangle className="size-3.5" />
                Motivo para não abordar
              </h4>
              <p className="mt-1.5 text-sm leading-relaxed">{analise.motivo_nao_abordar}</p>
            </div>
          )}

          {analise.oportunidade && (
            <Secao titulo="Oportunidade">
              <p>{analise.oportunidade}</p>
            </Secao>
          )}

          {analise.evidencias.length > 0 && (
            <Secao titulo="Evidências">
              <ul className="space-y-1">
                {analise.evidencias.map((item, i) => (
                  <li key={i} className="flex gap-2 text-muted-foreground">
                    <span className="text-success">•</span>
                    {item}
                  </li>
                ))}
              </ul>
            </Secao>
          )}

          {analise.impacto && (
            <Secao titulo="Impacto">
              <p>{analise.impacto}</p>
            </Secao>
          )}

          {analise.solucao && (
            <Secao titulo="Solução">
              <p>{analise.solucao}</p>
            </Secao>
          )}

          <Secao titulo="Micro-demo sugerida">
            <p>{LABEL_MICRO_DEMO[analise.micro_demo]}</p>
          </Secao>

          {analise.angulo && (
            <Secao titulo="Ângulo">
              <p>{analise.angulo}</p>
            </Secao>
          )}

          {analise.desconhecido.length > 0 && (
            <div>
              <h4 className={TITULO_SECAO}>Não verificado</h4>
              <ul className="mt-1.5 space-y-1">
                {analise.desconhecido.map((item, i) => (
                  <li key={i} className="flex gap-2 text-xs text-muted-foreground">
                    <span>•</span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <p className="text-[11px] text-muted-foreground">
            via {analise.provedor || "?"} · {formatarData(analise.criada_em)}
          </p>
        </div>
      )}
    </div>
  )
}
