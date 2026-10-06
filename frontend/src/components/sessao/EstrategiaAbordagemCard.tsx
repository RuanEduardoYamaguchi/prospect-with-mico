import { useEffect, useState } from "react"
import { ChevronDown, FileText, Loader2, Save, Sparkles } from "lucide-react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"
import { configService } from "@/services/configService"

const CHAVE_QUERY = ["estrategia-abordagem"]

/** Editor do estrategia_abordagem.md: o texto que manda no gerador de
 * mensagens. Salvou, vale na próxima mensagem gerada. */
export function EstrategiaAbordagemCard({ abertoInicial = false }: { abertoInicial?: boolean }) {
  const queryClient = useQueryClient()
  const [aberto, setAberto] = useState(abertoInicial)
  const [texto, setTexto] = useState("")

  const { data, isLoading } = useQuery({
    queryKey: CHAVE_QUERY,
    queryFn: configService.obterEstrategiaAbordagem,
  })

  useEffect(() => {
    if (data) setTexto(data.texto)
  }, [data])

  const salvar = useMutation({
    mutationFn: () => configService.salvarEstrategiaAbordagem(texto),
    onSuccess: () => {
      queryClient.setQueryData(CHAVE_QUERY, {
        texto,
        maximo: data?.maximo ?? 12000,
        modelo: data?.modelo ?? "",
      })
      queryClient.invalidateQueries({ queryKey: ["onboarding"] })
      toast.success("Estratégia salva. A próxima mensagem gerada já segue ela.")
    },
  })

  const alterado = data !== undefined && texto !== data.texto
  const maximo = data?.maximo ?? 12000
  const passouDoLimite = texto.length > maximo
  // modelo com [PREENCHER: ...] sobrando: a IA copiaria o marcador pras mensagens
  const temMarcador = texto.includes("[PREENCHER")
  const podeUsarModelo = !texto.trim() && Boolean(data?.modelo)

  return (
    <div className="rounded-xl border border-border bg-card">
      <button
        type="button"
        onClick={() => setAberto((v) => !v)}
        className="flex w-full items-center justify-between gap-2 p-4 text-left"
        aria-expanded={aberto}
      >
        <span className="flex items-center gap-2">
          <FileText className="size-4 text-muted-foreground" />
          <span className="font-medium">Estratégia de abordagem</span>
          {alterado && (
            <span className="rounded-full bg-warning/15 px-2 py-0.5 text-xs font-medium text-warning">
              não salvo
            </span>
          )}
        </span>
        <ChevronDown
          className={cn("size-4 text-muted-foreground transition-transform", aberto && "rotate-180")}
        />
      </button>

      {aberto && (
        <div className="space-y-3 border-t border-border p-4">
          <p className="text-sm text-muted-foreground">
            É o que a IA segue ao gerar a mensagem de cada lead: o que oferecer, tom,
            tamanho, o que nunca fazer e exemplos. Escreva como explicaria pra alguém
            novo no time. Deixar vazio volta pro padrão (oferta de site).
          </p>

          {podeUsarModelo && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setTexto(data?.modelo ?? "")}
            >
              <Sparkles className="size-4" />
              Começar pelo modelo
            </Button>
          )}

          {temMarcador && (
            <p className="rounded-lg bg-warning/10 p-2 text-xs text-warning">
              Ainda há trechos [PREENCHER: ...] no texto. Troque ou apague cada um
              pra poder salvar.
            </p>
          )}

          {isLoading ? (
            <div className="flex h-40 items-center justify-center">
              <Loader2 className="size-5 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <Textarea
              value={texto}
              onChange={(e) => setTexto(e.target.value)}
              className="min-h-[360px] font-mono text-[13px] leading-relaxed"
              spellCheck={false}
              aria-label="Estratégia de abordagem em Markdown"
            />
          )}

          <div className="flex flex-wrap items-center justify-between gap-2">
            <span
              className={cn(
                "text-xs tabular-nums",
                passouDoLimite ? "text-destructive" : "text-muted-foreground"
              )}
            >
              {texto.length.toLocaleString("pt-BR")} / {maximo.toLocaleString("pt-BR")} caracteres
            </span>
            <div className="flex gap-2">
              {alterado && (
                <Button variant="ghost" size="sm" onClick={() => setTexto(data?.texto ?? "")}>
                  Descartar
                </Button>
              )}
              <Button
                size="sm"
                onClick={() => salvar.mutate()}
                disabled={!alterado || passouDoLimite || temMarcador || salvar.isPending}
              >
                {salvar.isPending ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <Save className="size-4" />
                )}
                Salvar
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
