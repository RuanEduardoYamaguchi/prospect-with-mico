import { X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { SearchInput } from "@/components/filters/SearchInput"
import { StatusSelect } from "@/components/filters/StatusSelect"
import { NichoSelect } from "@/components/filters/NichoSelect"
import { NotaMinSelect } from "@/components/filters/NotaMinSelect"
import { OrdenacaoLeadsSelect } from "@/components/filters/OrdenacaoLeadsSelect"
import { SituacaoSiteSelect } from "@/components/filters/SituacaoSiteSelect"
import type { FiltrosLeads } from "@/types/lead"

interface LeadFilterBarProps {
  filtros: FiltrosLeads
  setFiltros: React.Dispatch<React.SetStateAction<FiltrosLeads>>
  filtrosEmUso: boolean
  onLimpar: () => void
  buscaInputRef?: React.Ref<HTMLInputElement>
}

export function LeadFilterBar({
  filtros,
  setFiltros,
  filtrosEmUso,
  onLimpar,
  buscaInputRef,
}: LeadFilterBarProps) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <SearchInput
        ref={buscaInputRef}
        valor={filtros.busca}
        onChange={(busca) => setFiltros((f) => ({ ...f, busca }))}
      />
      <StatusSelect
        valor={filtros.status}
        onChange={(status) => setFiltros((f) => ({ ...f, status }))}
      />
      <NichoSelect
        valor={filtros.nicho}
        onChange={(nicho) => setFiltros((f) => ({ ...f, nicho }))}
      />
      <NotaMinSelect
        valor={filtros.nota_min}
        onChange={(nota_min) => setFiltros((f) => ({ ...f, nota_min }))}
      />
      <SituacaoSiteSelect
        valor={filtros.site_status}
        onChange={(site_status) => setFiltros((f) => ({ ...f, site_status }))}
      />
      <OrdenacaoLeadsSelect
        valor={filtros.ordenar}
        onChange={(ordenar) => setFiltros((f) => ({ ...f, ordenar }))}
      />
      {filtrosEmUso && (
        <Button variant="ghost" size="sm" onClick={onLimpar}>
          <X className="size-4" />
          Limpar filtros
        </Button>
      )}
    </div>
  )
}
