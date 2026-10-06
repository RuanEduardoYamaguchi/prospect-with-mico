import { LinkIcon, MessageSquareText, TriangleAlert } from "lucide-react"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import {
  PRESETS_CAMPANHA,
  VARIAVEIS_TEMPLATE,
  templateTemLink,
  templateTemMarcador,
} from "@/lib/presetsCampanha"
import { cn } from "@/lib/utils"

interface TemplateCampanhaFormProps {
  template: string
  onChange: (template: string) => void
}

export function TemplateCampanhaForm({ template, onChange }: TemplateCampanhaFormProps) {
  const temLink = templateTemLink(template)
  const temMarcador = templateTemMarcador(template)

  const inserirVariavel = (variavel: string) => {
    onChange(template ? `${template} ${variavel}` : variavel)
  }

  return (
    <div className="space-y-2.5 rounded-xl border border-border bg-card p-4">
      <div className="flex items-center gap-2">
        <MessageSquareText className="size-4 text-muted-foreground" />
        <h3 className="font-medium">Mensagem</h3>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {PRESETS_CAMPANHA.length > 0 && (
          <Select onValueChange={(titulo) => {
            const preset = PRESETS_CAMPANHA.find((p) => p.titulo === titulo)
            if (preset) onChange(preset.texto)
          }}>
            <SelectTrigger className="h-8 w-full text-xs sm:w-[260px]">
              <SelectValue placeholder="Usar template pronto" />
            </SelectTrigger>
            <SelectContent>
              {PRESETS_CAMPANHA.map((preset) => (
                <SelectItem key={preset.titulo} value={preset.titulo}>
                  {preset.titulo}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>

      <Label>Texto da campanha</Label>
      <Textarea
        value={template}
        onChange={(e) => onChange(e.target.value)}
        rows={7}
        placeholder={"{Oi|Olá}, tudo bem? Aqui é o [seu nome], da [sua empresa]..."}
        className="font-mono text-xs"
      />

      <div className="flex flex-wrap items-center gap-1.5">
        {VARIAVEIS_TEMPLATE.map((variavel) => (
          <button
            key={variavel}
            type="button"
            onClick={() => inserirVariavel(variavel)}
            title="Clique pra inserir no fim do texto"
          >
            <Badge variant="outline" className="cursor-pointer hover:bg-muted">
              {variavel}
            </Badge>
          </button>
        ))}
        <span className="text-xs text-muted-foreground">
          e <code className="rounded bg-muted px-1 py-0.5">{"{a|b}"}</code> pra variar a frase
        </span>
      </div>

      {temMarcador && (
        <p className="flex items-center gap-1.5 rounded-lg bg-warning/10 p-2 text-xs text-warning">
          <TriangleAlert className="size-3.5 shrink-0" />
          Troque os trechos [PREENCHER: ...] pelo seu nome e o da sua empresa antes
          de iniciar a campanha.
        </p>
      )}

      {temLink && (
        <p
          className={cn(
            "flex items-center gap-1.5 rounded-lg bg-destructive/10 p-2 text-xs text-destructive"
          )}
        >
          <LinkIcon className="size-3.5 shrink-0" />
          Esse texto parece ter um link - a campanha recusa envio com link no
          primeiro contato. Link fica pro segundo contato, depois que a pessoa
          responder.
        </p>
      )}
    </div>
  )
}
