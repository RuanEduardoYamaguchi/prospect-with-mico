import { httpClient } from "@/services/httpClient"
import type { Onboarding } from "@/types/onboarding"

export const onboardingService = {
  obter: () => httpClient.get<Onboarding>("/api/onboarding"),
}
