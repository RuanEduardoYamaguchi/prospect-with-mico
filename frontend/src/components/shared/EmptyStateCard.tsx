import { cn } from "@/lib/utils"

interface EmptyStateCardProps {
  icone: React.ReactNode
  titulo: string
  descricao?: string
  acao?: React.ReactNode
  className?: string
}

/** Estado vazio padrão: ícone recuado, título curto, dica opcional e uma ação.
 * Usar sempre que uma seção/gráfico não tem dados - nunca mostrar eixos nus
 * ou uma linha de texto solta. */
export function EmptyStateCard({
  icone,
  titulo,
  descricao,
  acao,
  className,
}: EmptyStateCardProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-border bg-muted/20 px-6 py-10 text-center",
        className
      )}
    >
      <div className="flex size-10 items-center justify-center rounded-full bg-muted text-muted-foreground">
        {icone}
      </div>
      <p className="text-sm font-medium">{titulo}</p>
      {descricao && (
        <p className="max-w-sm text-xs text-muted-foreground">{descricao}</p>
      )}
      {acao && <div className="mt-1.5">{acao}</div>}
    </div>
  )
}
