import { useFunil } from "@/hooks/useAnalytics"
import { FunilConversaoChart } from "@/components/dashboard/FunilConversaoChart"

export function FunilConversao() {
  const { data, isLoading } = useFunil()

  return <FunilConversaoChart estagios={data?.estagios} isLoading={isLoading} />
}
