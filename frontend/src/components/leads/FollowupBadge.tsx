import { Clock } from "lucide-react"

export function FollowupBadge() {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-warning px-2 py-0.5 text-xs font-semibold text-warning-foreground shadow-sm">
      <Clock className="size-3" />
      Follow-up hoje
    </span>
  )
}
