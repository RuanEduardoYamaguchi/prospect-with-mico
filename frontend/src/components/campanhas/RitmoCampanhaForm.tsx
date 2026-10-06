import { Timer } from "lucide-react"
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import type { RitmoCampanha } from "@/types/whatsapp"

interface RitmoCampanhaFormProps {
  ritmo: RitmoCampanha
  onChange: (ritmo: RitmoCampanha) => void
  checarWhatsapp: boolean
  onChangeCheckarWhatsapp: (v: boolean) => void
}

export function RitmoCampanhaForm({
  ritmo,
  onChange,
  checarWhatsapp,
  onChangeCheckarWhatsapp,
}: RitmoCampanhaFormProps) {
  const set = <K extends keyof RitmoCampanha>(chave: K, valor: RitmoCampanha[K]) =>
    onChange({ ...ritmo, [chave]: valor })

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <Accordion type="single" collapsible defaultValue={undefined}>
        <AccordionItem value="ritmo" className="border-none">
          <AccordionTrigger className="py-0 hover:no-underline">
            <span className="inline-flex items-center gap-2">
              <Timer className="size-4 text-muted-foreground" />
              Ritmo do disparo
            </span>
          </AccordionTrigger>
          <AccordionContent>
            <div className="grid gap-3 pt-2 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label>Intervalo mínimo (s)</Label>
                <Input
                  type="number"
                  min={5}
                  value={ritmo.intervalo_min_s}
                  onChange={(e) => set("intervalo_min_s", Number(e.target.value))}
                />
              </div>
              <div className="space-y-1.5">
                <Label>Intervalo máximo (s)</Label>
                <Input
                  type="number"
                  min={5}
                  value={ritmo.intervalo_max_s}
                  onChange={(e) => set("intervalo_max_s", Number(e.target.value))}
                />
              </div>
              <div className="space-y-1.5">
                <Label>Pausa longa a cada (envios)</Label>
                <Input
                  type="number"
                  min={0}
                  value={ritmo.pausa_a_cada}
                  onChange={(e) => set("pausa_a_cada", Number(e.target.value))}
                />
              </div>
              <div className="space-y-1.5">
                <Label>Duração da pausa (s)</Label>
                <Input
                  type="number"
                  min={0}
                  value={ritmo.pausa_s}
                  onChange={(e) => set("pausa_s", Number(e.target.value))}
                />
              </div>
              <div className="space-y-1.5">
                <Label>Janela: das</Label>
                <Input
                  type="time"
                  value={ritmo.janela_inicio}
                  onChange={(e) => set("janela_inicio", e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label>até às</Label>
                <Input
                  type="time"
                  value={ritmo.janela_fim}
                  onChange={(e) => set("janela_fim", e.target.value)}
                />
              </div>
            </div>
          </AccordionContent>
        </AccordionItem>
      </Accordion>

      <div className="flex items-center justify-between gap-2 border-t border-border pt-3">
        <Label className="font-normal text-foreground">
          Checar se o número tem WhatsApp antes de enviar
        </Label>
        <Switch checked={checarWhatsapp} onCheckedChange={onChangeCheckarWhatsapp} />
      </div>
    </div>
  )
}
