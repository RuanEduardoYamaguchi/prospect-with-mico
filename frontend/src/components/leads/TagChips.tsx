import { tagsParaLista } from "@/lib/formatters"

interface TagChipsProps {
  tags: string | null
}

export function TagChips({ tags }: TagChipsProps) {
  const lista = tagsParaLista(tags)
  if (lista.length === 0) return null

  return (
    <div className="flex flex-wrap gap-1.5">
      {lista.map((tag) => (
        <span
          key={tag}
          className="rounded-full bg-status-purple/15 px-2 py-0.5 text-xs font-medium text-status-purple"
        >
          {tag}
        </span>
      ))}
    </div>
  )
}
