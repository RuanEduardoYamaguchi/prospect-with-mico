import { useEffect, useState } from "react"
import { Target } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  useAnaliseOportunidadeConfig,
  useSalvarAnaliseOportunidadeConfig,
} from "@/hooks/useConfiguracoes"

export function AnaliseOportunidadeCard() {
  const { data, isLoading } = useAnaliseOportunidadeConfig()
  const salvar = useSalvarAnaliseOportunidadeConfig()
  const [valor, setValor] = useState("")

  useEffect(() => {
    if (data) setValor(String(data.score_min))
  }, [data])

  const numero = Number(valor)
  const valido = valor.trim() !== "" && Number.isInteger(numero) && numero >= 0 && numero <= 100

  if (isLoading) return null

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4">
      <div className="flex items-center gap-2">
        <Target className="size-4 text-muted-foreground" />
        <h3 className="font-medium">Análise de oportunidade</h3>
      </div>

      <p className="text-sm text-muted-foreground">
        Só leads com score igual ou acima disso mostram o botão de análise. Cada análise
        gasta uma chamada de IA.
      </p>

      <div className="space-y-1.5">
        <Label htmlFor="score-min-oportunidade">
          Score mínimo para análise de oportunidade
        </Label>
        <Input
          id="score-min-oportunidade"
          type="number"
          min={0}
          max={100}
          step={1}
          value={valor}
          onChange={(e) => setValor(e.target.value)}
          className="w-32"
        />
      </div>

      <Button
        size="sm"
        className="w-fit"
        disabled={salvar.isPending || !valido}
        onClick={() => salvar.mutate(numero)}
      >
        {salvar.isPending ? "Salvando..." : "Salvar"}
      </Button>
    </div>
  )
}
