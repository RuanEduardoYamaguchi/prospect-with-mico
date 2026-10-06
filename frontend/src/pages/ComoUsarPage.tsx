import { BookOpen } from "lucide-react"
import { Header } from "@/components/layout/Header"
import { PrimeirosPassosCard } from "@/components/onboarding/PrimeirosPassosCard"
import { PageHero } from "@/components/shared/PageHero"

const PASSOS = [
  {
    titulo: "1. Buscar leads",
    texto:
      "Em Leads, clique em Nova busca. Escolha um nicho e uma cidade (ou solte pinos no mapa). A busca usa a Google Places API e respeita um teto mensal de consultas pra você ficar na cota gratuita. Também dá pra importar uma lista em CSV.",
  },
  {
    titulo: "2. Score",
    texto:
      "Cada lead recebe uma nota de 0 a 100 (reputação, volume de avaliações e situação do site). Como ponto de partida: 70 ou mais merece abordagem manual e personalizada; de 40 a 69 vai bem pra campanha em lote; abaixo de 40 não vale o esforço. Você muda essa faixa nos filtros da campanha.",
  },
  {
    titulo: "3. Hoje",
    texto:
      "Um lead por vez, com os follow-ups vencidos primeiro. Enter envia, seta pra direita pula, Backspace ignora.",
  },
  {
    titulo: "4. Envio",
    texto:
      "Com o WhatsApp conectado na página WhatsApp, a mensagem sai por ele, direto do sistema. Sem WhatsApp conectado, você copia a mensagem e envia pelo seu jeito de sempre.",
  },
  {
    titulo: "5. Conversa",
    texto:
      "As respostas do lead chegam sozinhas no sistema. A IA pode responder automaticamente (liga e desliga na página WhatsApp). Ela para quando o lead qualifica ou quando você responde pelo celular.",
  },
  {
    titulo: "6. Follow-up",
    texto:
      "O sistema agenda o follow-up 3 dias depois do contato. Ele aparece no Hoje quando vence.",
  },
  {
    titulo: "7. Campanhas",
    texto:
      "Disparo em lote com intervalo aleatório entre mensagens e janela de horário, sempre em chip separado do seu número oficial. Começa com volume baixo e sobe aos poucos, pra não queimar o número.",
  },
]

export function ComoUsarPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <Header />

      <main className="mx-auto w-full max-w-3xl space-y-5 px-4 py-6 sm:px-6">
        <PageHero
          icone={<BookOpen className="size-6" />}
          titulo="Como usar"
          descricao="Primeiros passos e o fluxo do dia a dia: buscar, abordar, conversar, fazer follow-up."
          gradiente="from-google-maps-start/85 via-primary/85 to-google-maps-end/85"
        />

        <PrimeirosPassosCard sempreVisivel />

        <div className="grid gap-3">
          {PASSOS.map((p) => (
            <section key={p.titulo} className="rounded-xl border border-border bg-card p-4">
              <h3 className="font-semibold tracking-tight">{p.titulo}</h3>
              <p className="mt-1 text-sm text-muted-foreground">{p.texto}</p>
            </section>
          ))}
        </div>
      </main>
    </div>
  )
}
