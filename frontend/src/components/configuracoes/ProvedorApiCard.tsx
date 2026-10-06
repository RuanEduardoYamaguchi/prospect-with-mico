import { useState } from "react"
import { CheckCircle2, ExternalLink, KeyRound } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useSalvarConfiguracao } from "@/hooks/useConfiguracoes"
import type { ConfiguracaoProvedor, ProvedorIA } from "@/types/config"

interface ProvedorApiCardProps {
  provedor: ProvedorIA
  titulo: string
  config: ConfiguracaoProvedor
}

export function ProvedorApiCard({ provedor, titulo, config }: ProvedorApiCardProps) {
  const [valor, setValor] = useState("")
  const salvar = useSalvarConfiguracao()

  const handleSalvar = () => {
    if (!valor.trim()) return
    salvar.mutate(
      { chave: provedor, valor: valor.trim() },
      { onSuccess: () => setValor("") }
    )
  }

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <KeyRound className="size-4 text-muted-foreground" />
          <h3 className="font-medium">{titulo}</h3>
        </div>
        {config.configurada ? (
          <span className="inline-flex items-center gap-1 rounded-full bg-success/15 px-2 py-0.5 text-xs font-medium text-success">
            <CheckCircle2 className="size-3.5" />
            Configurada · {config.mascarada}
          </span>
        ) : (
          <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
            Não configurada
          </span>
        )}
      </div>

      <div className="space-y-1.5">
        <Label>Chave de API</Label>
        <div className="flex gap-2">
          <Input
            type="password"
            autoComplete="off"
            value={valor}
            onChange={(e) => setValor(e.target.value)}
            placeholder={config.configurada ? "Digite para substituir a chave atual" : "Cole sua chave de API aqui"}
          />
          <Button
            size="sm"
            disabled={!valor.trim() || salvar.isPending}
            onClick={handleSalvar}
          >
            {salvar.isPending ? "Salvando..." : "Salvar"}
          </Button>
        </div>
      </div>

      <a
        href={config.link_obter_chave}
        target="_blank"
        rel="noreferrer"
        className="inline-flex w-fit items-center gap-1 text-xs text-muted-foreground hover:text-foreground hover:underline"
      >
        <ExternalLink className="size-3" />
        Obtenha sua chave aqui
      </a>
    </div>
  )
}
