import { LABEL_STATUS } from "@/lib/constants"
import { STATUS_VALIDOS, type StatusLead } from "@/types/lead"
import { SelectComVazio } from "@/components/filters/SelectComVazio"

interface StatusSelectProps {
  valor: StatusLead | ""
  onChange: (valor: StatusLead | "") => void
}

export function StatusSelect({ valor, onChange }: StatusSelectProps) {
  return (
    <SelectComVazio
      valor={valor}
      onChange={(v) => onChange(v as StatusLead | "")}
      opcoes={STATUS_VALIDOS.map((status) => ({
        valor: status,
        label: LABEL_STATUS[status],
      }))}
      labelVazio="Todos os status"
      placeholder="Status"
      className="w-[160px]"
    />
  )
}
