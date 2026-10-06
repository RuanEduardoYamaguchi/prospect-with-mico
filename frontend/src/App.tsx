import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"
import { QueryClientProvider } from "@tanstack/react-query"
import { TooltipProvider } from "@/components/ui/tooltip"
import { Toaster } from "@/components/ui/sonner"
import { queryClient } from "@/lib/queryClient"
import { PaletaComando } from "@/components/shared/PaletaComando"
import { DashboardPage } from "@/pages/DashboardPage"
import { HojePage } from "@/pages/HojePage"
import { ComoUsarPage } from "@/pages/ComoUsarPage"
import { LeadsMapsPage } from "@/pages/LeadsMapsPage"
import { WhatsAppPage } from "@/pages/WhatsAppPage"
import { CampanhasPage } from "@/pages/CampanhasPage"
import { ConversaPage } from "@/pages/ConversaPage"
import { ConfiguracoesPage } from "@/pages/ConfiguracoesPage"

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <BrowserRouter>
          <PaletaComando />
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/hoje" element={<HojePage />} />
            <Route path="/leads" element={<LeadsMapsPage />} />
            <Route path="/whatsapp" element={<WhatsAppPage />} />
            <Route path="/campanhas" element={<CampanhasPage />} />
            <Route path="/conversas/:placeId" element={<ConversaPage />} />
            <Route path="/configuracoes" element={<ConfiguracoesPage />} />
            <Route path="/como-usar" element={<ComoUsarPage />} />
            <Route path="/tarefas" element={<Navigate to="/hoje" replace />} />
            <Route path="/sessao" element={<Navigate to="/hoje" replace />} />
            <Route path="/instagram" element={<Navigate to="/" replace />} />
            <Route path="/instagram/analytics" element={<Navigate to="/" replace />} />
            <Route path="/instagram/arquivados" element={<Navigate to="/" replace />} />
            <Route path="/analytics" element={<Navigate to="/" replace />} />
            <Route path="/documentacao" element={<Navigate to="/como-usar" replace />} />
          </Routes>
        </BrowserRouter>
        <Toaster position="bottom-right" richColors />
      </TooltipProvider>
    </QueryClientProvider>
  )
}
