import { ArrowLeft, MessageCircle, ShieldAlert } from "lucide-react"
import { Link } from "react-router-dom"
import { Header } from "@/components/layout/Header"
import { PageHero } from "@/components/shared/PageHero"
import { ConexaoWhatsappCard } from "@/components/whatsapp/ConexaoWhatsappCard"
import { AquecimentoCard } from "@/components/whatsapp/AquecimentoCard"
import { AutorespostaCard } from "@/components/whatsapp/AutorespostaCard"
import { EnviarNumeroCard } from "@/components/whatsapp/EnviarNumeroCard"

export function WhatsAppPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <Header />

      <main className="mx-auto w-full max-w-3xl space-y-6 px-4 py-6 sm:px-6">
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-4" />
          Voltar para o dashboard
        </Link>

        <PageHero
          icone={<MessageCircle className="size-6" />}
          titulo="WhatsApp"
          descricao="Chip de disparo separado do seu número oficial, conectado pela Evolution API local."
          gradiente="from-success/80 via-success/70 to-success/85"
        />

        <div className="grid gap-4 sm:grid-cols-2">
          <ConexaoWhatsappCard />
          <AquecimentoCard />
        </div>

        <AutorespostaCard />

        <EnviarNumeroCard />

        <div className="space-y-2 rounded-xl border border-warning/30 bg-warning/10 p-4">
          <div className="flex items-center gap-2">
            <ShieldAlert className="size-4 shrink-0 text-warning" />
            <h3 className="font-medium">Cuidado com o número</h3>
          </div>
          <ul className="list-inside list-disc space-y-1 text-sm text-muted-foreground">
            <li>
              Disparo sempre em chip separado do seu número oficial - nunca no
              número principal do seu negócio.
            </li>
            <li>Chip novo começa com volume baixo e sobe aos poucos.</li>
            <li>Sem link no primeiro contato - só depois que a pessoa responde.</li>
            <li>Quem diz "não" ou pede pra sair, remove da lista na hora.</li>
          </ul>
        </div>
      </main>
    </div>
  )
}
