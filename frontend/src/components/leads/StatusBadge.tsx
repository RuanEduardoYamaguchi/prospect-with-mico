import { Badge } from "@/components/ui/badge"
import { COR_STATUS, LABEL_STATUS } from "@/lib/constants"
import { cn } from "@/lib/utils"
import type { StatusLead } from "@/types/lead"

interface StatusBadgeProps {
  status: StatusLead
}

export function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <Badge
      variant="outline"
      className={cn("font-medium uppercase tracking-wide", COR_STATUS[status])}
    >
      {LABEL_STATUS[status]}
    </Badge>
  )
}
