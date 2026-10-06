import { CheckCircle2, Info } from "lucide-react"
import type { EstadoBusca } from "@/types/busca"

interface BuscaResultadoProps {
  estado: EstadoBusca
}

function ehResultadoSemLeadsNovos(mensagem: string): boolean {
  return (
    mensagem.includes("nenhum lead novo") ||
    mensagem.includes("nenhuma empresa foi encontrada")
  )
}

export function BuscaResultado({ estado }: BuscaResultadoProps) {
  const semNovidade = ehResultadoSemLeadsNovos(estado.mensagem)

  return (
    <div
      className={
        semNovidade
          ? "flex gap-2.5 rounded-lg border border-warning/30 bg-warning/10 p-3 text-sm"
          : "flex gap-2.5 rounded-lg border border-success/30 bg-success/10 p-3 text-sm"
      }
    >
      {semNovidade ? (
        <Info className="mt-0.5 size-4 shrink-0 text-warning" />
      ) : (
        <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-success" />
      )}
      <div className="space-y-1">
        <p className="font-medium">{estado.mensagem}</p>
        {semNovidade && (
          <p className="text-xs text-muted-foreground">
            Isso costuma acontecer em cidades grandes, onde a maioria dos
            negócios já tem site. Tente uma cidade menor (100-500 mil
            habitantes) ou outro nicho.
          </p>
        )}
      </div>
    </div>
  )
}
