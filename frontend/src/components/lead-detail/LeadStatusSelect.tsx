import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Label } from "@/components/ui/label"
import { LABEL_STATUS } from "@/lib/constants"
import { STATUS_VALIDOS, type StatusLead } from "@/types/lead"

interface LeadStatusSelectProps {
  status: StatusLead
  onChange: (status: StatusLead) => void
}

export function LeadStatusSelect({ status, onChange }: LeadStatusSelectProps) {
  return (
    <div className="space-y-1.5">
      <Label>Status</Label>
      <Select value={status} onValueChange={(v) => onChange(v as StatusLead)}>
        <SelectTrigger className="w-full">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {STATUS_VALIDOS.map((s) => (
            <SelectItem key={s} value={s}>
              {LABEL_STATUS[s]}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}
