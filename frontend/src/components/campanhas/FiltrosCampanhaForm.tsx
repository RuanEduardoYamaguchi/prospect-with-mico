import { Filter } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { NichoSelect } from "@/components/filters/NichoSelect"
import type { FiltrosCampanha } from "@/types/whatsapp"

interface FiltrosCampanhaFormProps {
  filtros: FiltrosCampanha
  onChange: (filtros: FiltrosCampanha) => void
  limite: number
  onChangeLimite: (limite: number) => void
}

function LinhaSwitch({
  label,
  checked,
  onCheckedChange,
}: {
  label: string
  checked: boolean
  onCheckedChange: (v: boolean) => void
}) {
  return (
    <div className="flex items-center justify-between gap-2">
      <Label className="font-normal text-foreground">{label}</Label>
      <Switch checked={checked} onCheckedChange={onCheckedChange} />
    </div>
  )
}

export function FiltrosCampanhaForm({
  filtros,
  onChange,
  limite,
  onChangeLimite,
}: FiltrosCampanhaFormProps) {
  const set = <K extends keyof FiltrosCampanha>(chave: K, valor: FiltrosCampanha[K]) =>
    onChange({ ...filtros, [chave]: valor })

  return (
    <div className="space-y-4 rounded-xl border border-border bg-card p-4">
      <div className="flex items-center gap-2">
        <Filter className="size-4 text-muted-foreground" />
        <h3 className="font-medium">Quem entra na campanha</h3>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label>Nicho</Label>
          <NichoSelect
            valor={filtros.nicho ?? ""}
            onChange={(v) => set("nicho", v || null)}
          />
        </div>
        <div className="space-y-1.5">
          <Label>Cidade</Label>
          <Input
            value={filtros.cidade ?? ""}
            onChange={(e) => set("cidade", e.target.value || null)}
            placeholder="Ex: Curitiba"
          />
        </div>
      </div>

      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <Label>Faixa de score</Label>
          <span className="text-xs tabular-nums text-muted-foreground">
            {filtros.score_min} a {filtros.score_max}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Input
            type="number"
            min={0}
            max={100}
            value={filtros.score_min}
            onChange={(e) => set("score_min", Number(e.target.value))}
          />
          <span className="text-xs text-muted-foreground">até</span>
          <Input
            type="number"
            min={0}
            max={100}
            value={filtros.score_max}
            onChange={(e) => set("score_max", Number(e.target.value))}
          />
        </div>
        <p className="text-xs text-muted-foreground">
          70+ é abordagem manual, pela Sessão de prospecção - a campanha não
          pega esses leads por padrão.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label>Máx. de avaliações</Label>
          <Input
            type="number"
            min={0}
            value={filtros.max_avaliacoes ?? ""}
            onChange={(e) =>
              set("max_avaliacoes", e.target.value === "" ? null : Number(e.target.value))
            }
            placeholder="Sem limite"
          />
        </div>
        <div className="space-y-1.5">
          <Label>Limite de disparos</Label>
          <Input
            type="number"
            min={1}
            value={limite}
            onChange={(e) => onChangeLimite(Number(e.target.value))}
          />
        </div>
      </div>

      <div className="space-y-2.5 border-t border-border pt-3">
        <LinhaSwitch
          label="Só quem não tem site"
          checked={filtros.sem_site}
          onCheckedChange={(v) => set("sem_site", v)}
        />
        <LinhaSwitch
          label="Só quem não tem Instagram"
          checked={filtros.sem_instagram}
          onCheckedChange={(v) => set("sem_instagram", v)}
        />
        <LinhaSwitch
          label="Só celular (sem fixo)"
          checked={filtros.so_celular}
          onCheckedChange={(v) => set("so_celular", v)}
        />
        <LinhaSwitch
          label="Pular quem já foi contatado"
          checked={filtros.pular_contatados}
          onCheckedChange={(v) => set("pular_contatados", v)}
        />
      </div>
    </div>
  )
}
