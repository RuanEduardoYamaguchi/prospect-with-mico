import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

const SENTINELA_VAZIO = "__vazio__"

interface Opcao {
  valor: string
  label: string
}

interface SelectComVazioProps {
  valor: string
  onChange: (valor: string) => void
  opcoes: Opcao[]
  labelVazio: string
  placeholder: string
  className?: string
}

export function SelectComVazio({
  valor,
  onChange,
  opcoes,
  labelVazio,
  placeholder,
  className,
}: SelectComVazioProps) {
  return (
    <Select
      value={valor || SENTINELA_VAZIO}
      onValueChange={(v) => onChange(v === SENTINELA_VAZIO ? "" : v)}
    >
      <SelectTrigger className={className}>
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value={SENTINELA_VAZIO}>{labelVazio}</SelectItem>
        {opcoes.map((opcao) => (
          <SelectItem key={opcao.valor} value={opcao.valor}>
            {opcao.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
