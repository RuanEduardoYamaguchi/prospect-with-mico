import { useState } from "react"
import { Send } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { useEnviarNumeroWhatsapp, useEstadoWhatsapp } from "@/hooks/useWhatsapp"

export function EnviarNumeroCard() {
  const { data: estado } = useEstadoWhatsapp()
  const enviar = useEnviarNumeroWhatsapp()
  const [telefone, setTelefone] = useState("")
  const [texto, setTexto] = useState("")

  const conectado = Boolean(estado?.conectado)
  const podeEnviar = conectado && telefone.trim() !== "" && texto.trim() !== "" && !enviar.isPending

  const handleEnviar = () => {
    enviar.mutate(
      { telefone, texto },
      {
        onSuccess: () => setTexto(""),
      },
    )
  }

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4">
      <div className="flex items-center gap-2">
        <Send className="size-4 text-muted-foreground" />
        <h3 className="font-medium">Mandar mensagem pra um número</h3>
      </div>

      <p className="text-sm text-muted-foreground">
        Pra qualquer número, sem precisar ter um lead cadastrado. Útil pra teste ou contato
        avulso - não passa pelas travas de campanha.
      </p>

      <Input
        placeholder="Número com DDD (ex: 65999998888)"
        value={telefone}
        onChange={(evento) => setTelefone(evento.target.value)}
      />

      <Textarea
        placeholder="Texto da mensagem"
        value={texto}
        onChange={(evento) => setTexto(evento.target.value)}
        rows={3}
      />

      <Button onClick={handleEnviar} disabled={!podeEnviar} className="self-start">
        <Send className="size-4" />
        {enviar.isPending ? "Enviando..." : "Enviar"}
      </Button>

      {!conectado && (
        <p className="text-xs text-warning">Conecte o WhatsApp antes de enviar.</p>
      )}
    </div>
  )
}
