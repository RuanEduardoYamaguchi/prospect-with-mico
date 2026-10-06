import { Bot } from "lucide-react"
import { Skeleton } from "@/components/ui/skeleton"
import { Switch } from "@/components/ui/switch"
import { useAutoresposta, useDefinirAutoresposta } from "@/hooks/useWhatsapp"

export function AutorespostaCard() {
  const { data, isLoading } = useAutoresposta()
  const definir = useDefinirAutoresposta()

  if (isLoading || !data) return <Skeleton className="h-[110px] rounded-xl" />

  return (
    <div className="space-y-2 rounded-xl border border-border bg-card p-4">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Bot className="size-4 text-muted-foreground" />
          <h3 className="font-medium">Resposta automática da IA</h3>
        </div>
        <Switch
          checked={data.ativa}
          disabled={definir.isPending}
          onCheckedChange={(ativa) => definir.mutate(ativa)}
          aria-label="Resposta automática da IA"
        />
      </div>
      <p className="text-sm text-muted-foreground">
        Ligada, a IA responde sozinha quem escreve e para quando o lead qualifica ou
        quando vocês respondem pelo celular.
      </p>
      <p className="text-xs text-muted-foreground">
        Desligada, a IA não responde nem avisa quando um lead qualifica. Leads que vocês
        responderam pelo celular ficam pausados e precisam ser retomados um por um na
        Conversa. Religar não responde as mensagens antigas.
      </p>
    </div>
  )
}
