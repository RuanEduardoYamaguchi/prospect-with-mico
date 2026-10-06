import { useEffect, useState } from "react"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import type { Lead } from "@/types/lead"

interface LeadObservacoesFormProps {
  lead: Lead
  onSalvar: (observacoes: string) => void
  salvando: boolean
}

export function LeadObservacoesForm({
  lead,
  onSalvar,
  salvando,
}: LeadObservacoesFormProps) {
  const [observacoes, setObservacoes] = useState(lead.observacoes ?? "")

  useEffect(() => {
    setObservacoes(lead.observacoes ?? "")
  }, [lead.place_id, lead.observacoes])

  return (
    <div className="space-y-1.5">
      <Label>Observações</Label>
      <Textarea
        rows={3}
        value={observacoes}
        onChange={(e) => setObservacoes(e.target.value)}
        placeholder="Anotações sobre esse contato..."
      />
      <Button
        size="sm"
        variant="secondary"
        disabled={salvando}
        onClick={() => onSalvar(observacoes)}
      >
        {salvando ? "Salvando..." : "Salvar observações"}
      </Button>
    </div>
  )
}
