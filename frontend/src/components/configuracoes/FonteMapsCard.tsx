import { useState } from "react"
import { AlertTriangle, CheckCircle2, ExternalLink, KeyRound } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useFonteMaps, useSalvarFonteMaps } from "@/hooks/useConfiguracoes"
import { Skeleton } from "@/components/ui/skeleton"

export function FonteMapsCard() {
  const { data, isLoading } = useFonteMaps()
  const salvar = useSalvarFonteMaps()
  const [chave, setChave] = useState("")

  if (isLoading || !data) return <Skeleton className="h-[260px]" />

  const fonteAntiga = data.fonte === "scraper"
  const precisaDeChave = !data.chave_configurada && !chave.trim()
  const uso = data.uso_places

  const handleSalvar = () => {
    salvar.mutate(
      { fonte: "places", chave: chave.trim() || undefined },
      { onSuccess: () => setChave("") }
    )
  }

  return (
    <div className="flex flex-col gap-4 rounded-xl border border-border bg-card p-5">
      {fonteAntiga && (
        <div className="flex items-start gap-2 rounded-lg border border-border bg-muted/40 p-3 text-sm">
          <AlertTriangle className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
          <span>
            A fonte salva ainda é o scraper antigo, que não funciona mais. Ao
            salvar, a busca passa a usar o Google Places.
          </span>
        </div>
      )}

      <div className="space-y-1">
        <h3 className="font-medium">Google Places API</h3>
        <p className="text-sm text-muted-foreground">
          É daqui que vêm os negócios encontrados na busca. O teto é de 900
          consultas por mês, pra ficar na cota gratuita do Google.
        </p>
        {uso ? (
          <p className="text-sm font-medium">
            {uso.usadas} de {uso.teto} consultas este mês
          </p>
        ) : null}
      </div>

      <div className="space-y-2 border-t border-border pt-4">
        <div className="flex items-center justify-between gap-2">
          <span className="inline-flex items-center gap-2 text-sm font-medium">
            <KeyRound className="size-4 text-muted-foreground" />
            Chave da Google Places API
          </span>
          {data.chave_configurada ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-success/15 px-2 py-0.5 text-xs font-medium text-success">
              <CheckCircle2 className="size-3.5" />
              Configurada · {data.mascarada}
            </span>
          ) : (
            <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
              Não configurada
            </span>
          )}
        </div>

        <Input
          type="password"
          autoComplete="off"
          value={chave}
          onChange={(e) => setChave(e.target.value)}
          placeholder={
            data.chave_configurada
              ? "Digite somente para substituir a chave"
              : "Cole aqui a chave criada no Google Cloud"
          }
        />
        <p className="text-xs text-muted-foreground">
          A chave fica protegida no cofre de credenciais do Windows e nunca é
          enviada ao navegador depois de salva.
        </p>

        <a
          href={data.link_obter_chave}
          target="_blank"
          rel="noreferrer"
          className="inline-flex w-fit items-center gap-1 text-xs font-medium text-success hover:underline"
        >
          Abrir credenciais no Google Cloud
          <ExternalLink className="size-3" />
        </a>
      </div>

      <div className="flex items-center justify-between gap-3 border-t border-border pt-4">
        <p className="text-xs text-muted-foreground">
          A mudança vale apenas para novas buscas.
        </p>
        <Button size="sm" disabled={salvar.isPending || precisaDeChave} onClick={handleSalvar}>
          {salvar.isPending ? "Validando..." : "Validar e salvar"}
        </Button>
      </div>
    </div>
  )
}
