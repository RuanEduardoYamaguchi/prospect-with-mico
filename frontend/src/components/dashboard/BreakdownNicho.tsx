import { usePorNicho } from "@/hooks/useAnalytics"
import { BreakdownPorNicho } from "@/components/dashboard/BreakdownPorNicho"

export function BreakdownNicho() {
  const { data, isLoading } = usePorNicho()

  return (
    <BreakdownPorNicho
      nichos={data?.nichos}
      isLoading={isLoading}
      corBarra="bg-success"
    />
  )
}
