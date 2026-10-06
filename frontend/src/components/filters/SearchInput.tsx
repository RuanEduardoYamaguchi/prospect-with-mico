import { forwardRef } from "react"
import { Search } from "lucide-react"
import { Input } from "@/components/ui/input"

interface SearchInputProps {
  valor: string
  onChange: (valor: string) => void
}

export const SearchInput = forwardRef<HTMLInputElement, SearchInputProps>(
  function SearchInput({ valor, onChange }, ref) {
    return (
      <div className="relative flex-1 min-w-[200px]">
        <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          ref={ref}
          type="search"
          placeholder="Buscar por nome ou endereço... (atalho: /)"
          value={valor}
          onChange={(e) => onChange(e.target.value)}
          className="pl-8"
        />
      </div>
    )
  }
)
