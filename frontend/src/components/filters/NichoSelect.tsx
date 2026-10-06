import { useNichos } from "@/hooks/useNichos"
import { SelectComVazio } from "@/components/filters/SelectComVazio"

interface NichoSelectProps {
  valor: string
  onChange: (valor: string) => void
}

export function NichoSelect({ valor, onChange }: NichoSelectProps) {
  const { data: nichos } = useNichos()

  return (
    <SelectComVazio
      valor={valor}
      onChange={onChange}
      opcoes={(nichos ?? []).map((nicho) => ({ valor: nicho, label: nicho }))}
      labelVazio="Todos os nichos"
      placeholder="Nicho"
      className="w-[200px]"
    />
  )
}
