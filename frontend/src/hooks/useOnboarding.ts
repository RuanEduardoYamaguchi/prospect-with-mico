import { useQuery } from "@tanstack/react-query"
import { onboardingService } from "@/services/onboardingService"

/** Sempre refaz ao abrir a tela: a pessoa sai pra configurar uma chave e volta,
 * e o checklist tem que já estar marcado. */
export function useOnboarding() {
  return useQuery({
    queryKey: ["onboarding"],
    queryFn: onboardingService.obter,
    staleTime: 0,
    refetchOnMount: "always",
  })
}
