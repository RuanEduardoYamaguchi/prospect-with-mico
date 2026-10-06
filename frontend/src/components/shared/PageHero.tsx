import { cn } from "@/lib/utils"

interface PageHeroProps {
  icone: React.ReactNode
  titulo: string
  descricao: string
  /** Classes do gradiente de fundo (ex.: "from-google-maps-start/85 via-google-maps-mid/85 to-google-maps-end/85") */
  gradiente: string
  acoes?: React.ReactNode
}

/** Banner de identidade no topo de cada área do produto - mesmo layout em todas
 * as páginas, mudando só o gradiente/ícone do canal. */
export function PageHero({ icone, titulo, descricao, gradiente, acoes }: PageHeroProps) {
  return (
    <div
      className={cn(
        "flex items-center justify-between gap-4 rounded-2xl bg-gradient-to-r p-5 text-white shadow-sm",
        gradiente
      )}
    >
      <div className="flex items-center gap-4">
        <div className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-white/20 backdrop-blur">
          {icone}
        </div>
        <div>
          <h2 className="text-xl font-semibold tracking-tight">{titulo}</h2>
          <p className="text-sm text-white/85">{descricao}</p>
        </div>
      </div>

      {acoes && <div className="flex shrink-0 items-center gap-2">{acoes}</div>}
    </div>
  )
}

/** Classe dos botões/links translúcidos usados nas ações do PageHero. */
export const CLASSE_ACAO_HERO =
  "inline-flex items-center gap-1.5 rounded-lg bg-white/15 px-3 py-1.5 text-sm font-medium backdrop-blur transition-colors hover:bg-white/25"
