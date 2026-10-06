import { OPCOES_NOTA_MINIMA } from "@/lib/constants"
import { SelectComVazio } from "@/components/filters/SelectComVazio"
import type { FiltrosLeads } from "@/types/lead"

interface NotaMinSelectProps {
  valor: FiltrosLeads["nota_min"]
  onChange: (valor: FiltrosLeads["nota_min"]) => void
}

export function NotaMinSelect({ valor, onChange }: NotaMinSelectProps) {
  const opcoesSemVazio = OPCOES_NOTA_MINIMA.filter((o) => o.valor !== "")

  return (
    <SelectComVazio
      valor={valor}
      onChange={(v) => onChange(v as FiltrosLeads["nota_min"])}
      opcoes={opcoesSemVazio.map((o) => ({ valor: o.valor, label: o.label }))}
      labelVazio="Qualquer nota"
      placeholder="Nota mínima"
      className="w-[160px]"
    />
  )
}
