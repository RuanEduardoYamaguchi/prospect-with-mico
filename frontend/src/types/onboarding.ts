/** Resposta de GET /api/onboarding: o que já está configurado e o que falta. */
export interface Onboarding {
  ia_configurada: boolean
  places_configurada: boolean
  perfil_preenchido: boolean
  estrategia_personalizada: boolean
  total_leads: number
  leads_contatados: number
}
