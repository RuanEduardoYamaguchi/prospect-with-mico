import { AlertTriangle } from "lucide-react"

export function LeadDificilBadge() {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-destructive/15 px-2 py-0.5 text-xs font-semibold text-destructive">
      <AlertTriangle className="size-3" />
      Lead difícil
    </span>
  )
}
