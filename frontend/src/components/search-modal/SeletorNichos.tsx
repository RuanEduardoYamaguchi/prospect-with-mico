import { useMemo, useState } from "react"
import { Check, Plus, Search, X } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"
import {
  CATALOGO_NICHOS,
  LIMITE_NICHOS_POR_BUSCA,
  normalizarParaBusca,
} from "@/lib/nichos"

interface SeletorNichosProps {
  selecionados: string[]
  onChange: (nichos: string[]) => void
  desabilitado?: boolean
}

export function SeletorNichos({
  selecionados,
  onChange,
  desabilitado = false,
}: SeletorNichosProps) {
  const [filtro, setFiltro] = useState("")
  const [personalizado, setPersonalizado] = useState("")

  const selecionadosNormalizados = useMemo(
    () => new Set(selecionados.map(normalizarParaBusca)),
    [selecionados]
  )

  const categoriasFiltradas = useMemo(() => {
    const termo = normalizarParaBusca(filtro.trim())
    if (!termo) return CATALOGO_NICHOS
    return CATALOGO_NICHOS.map((c) => ({
      categoria: c.categoria,
      nichos: c.nichos.filter((n) => normalizarParaBusca(n).includes(termo)),
    })).filter((c) => c.nichos.length > 0)
  }, [filtro])

  const alternar = (nicho: string) => {
    if (desabilitado) return
    const chave = normalizarParaBusca(nicho)
    if (selecionadosNormalizados.has(chave)) {
      onChange(selecionados.filter((n) => normalizarParaBusca(n) !== chave))
      return
    }
    if (selecionados.length >= LIMITE_NICHOS_POR_BUSCA) {
      toast.warning(
        `Máximo de ${LIMITE_NICHOS_POR_BUSCA} nichos por busca - cada nicho é uma varredura completa em cada área.`
      )
      return
    }
    onChange([...selecionados, nicho])
  }

  const adicionarPersonalizado = () => {
    const texto = personalizado.trim()
    if (!texto) return
    alternar(texto)
    setPersonalizado("")
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs font-medium text-muted-foreground">
          Nichos a buscar em cada área
        </p>
        <span
          className={cn(
            "text-xs font-medium tabular-nums",
            selecionados.length >= LIMITE_NICHOS_POR_BUSCA
              ? "text-warning"
              : "text-muted-foreground"
          )}
        >
          {selecionados.length}/{LIMITE_NICHOS_POR_BUSCA}
        </span>
      </div>

      {selecionados.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {selecionados.map((nicho) => (
            <button
              key={nicho}
              type="button"
              onClick={() => alternar(nicho)}
              disabled={desabilitado}
              className="inline-flex items-center gap-1 rounded-full bg-primary/10 py-1 pl-2.5 pr-1.5 text-xs font-medium text-primary transition-colors hover:bg-primary/20"
              aria-label={`Remover nicho ${nicho}`}
            >
              {nicho}
              <X className="size-3" />
            </button>
          ))}
        </div>
      )}

      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={filtro}
            onChange={(e) => setFiltro(e.target.value)}
            placeholder="Filtrar nichos (ex: estética, advocacia...)"
            disabled={desabilitado}
            className="pl-8"
          />
        </div>
      </div>

      <div className="max-h-52 space-y-3 overflow-y-auto rounded-lg border border-border bg-muted/20 p-3">
        {categoriasFiltradas.length === 0 ? (
          <p className="py-2 text-center text-xs text-muted-foreground">
            Nenhum nicho do catálogo bate com "{filtro}" - adicione como
            personalizado logo abaixo.
          </p>
        ) : (
          categoriasFiltradas.map((categoria) => (
            <div key={categoria.categoria}>
              <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                {categoria.categoria}
              </p>
              <div className="flex flex-wrap gap-1.5">
                {categoria.nichos.map((nicho) => {
                  const ativo = selecionadosNormalizados.has(normalizarParaBusca(nicho))
                  return (
                    <button
                      key={nicho}
                      type="button"
                      onClick={() => alternar(nicho)}
                      disabled={desabilitado}
                      aria-pressed={ativo}
                      className={cn(
                        "inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs transition-colors",
                        ativo
                          ? "border-primary/40 bg-primary/15 font-medium text-primary"
                          : "border-border bg-card text-foreground hover:border-primary/40 hover:bg-primary/5"
                      )}
                    >
                      {ativo && <Check className="size-3" />}
                      {nicho}
                    </button>
                  )
                })}
              </div>
            </div>
          ))
        )}
      </div>

      <div className="flex gap-2">
        <Input
          value={personalizado}
          onChange={(e) => setPersonalizado(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault()
              adicionarPersonalizado()
            }
          }}
          placeholder="Nicho fora do catálogo? Digite e adicione..."
          disabled={desabilitado}
        />
        <Button
          type="button"
          variant="outline"
          onClick={adicionarPersonalizado}
          disabled={desabilitado || !personalizado.trim()}
          aria-label="Adicionar nicho personalizado"
        >
          <Plus className="size-4" />
        </Button>
      </div>
    </div>
  )
}
