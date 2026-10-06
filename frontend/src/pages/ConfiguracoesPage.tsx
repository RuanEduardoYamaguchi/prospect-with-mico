import { ArrowLeft, BookOpen } from "lucide-react"
import { Link } from "react-router-dom"
import { Header } from "@/components/layout/Header"
import { Skeleton } from "@/components/ui/skeleton"
import { AnaliseOportunidadeCard } from "@/components/configuracoes/AnaliseOportunidadeCard"
import { FonteMapsCard } from "@/components/configuracoes/FonteMapsCard"
import { PerfilVendedorCard } from "@/components/configuracoes/PerfilVendedorCard"
import { EstrategiaAbordagemCard } from "@/components/sessao/EstrategiaAbordagemCard"
import { ProvedorApiCard } from "@/components/configuracoes/ProvedorApiCard"
import { SomConfigCard } from "@/components/configuracoes/SomConfigCard"
import { useConfiguracoes } from "@/hooks/useConfiguracoes"

const TITULOS: Record<"anthropic" | "gemini" | "groq" | "nvidia" | "pagespeed", string> = {
  anthropic: "Claude (Anthropic)",
  gemini: "Google Gemini",
  groq: "Groq",
  nvidia: "NVIDIA",
  pagespeed: "Google PageSpeed (opcional)",
}

export function ConfiguracoesPage() {
  const { data, isLoading } = useConfiguracoes()

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Header />

      <main className="mx-auto w-full max-w-2xl space-y-6 px-4 py-6 sm:px-6">
        <div className="flex items-center justify-between gap-3">
          <Link
            to="/"
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="size-4" />
            Voltar para o dashboard
          </Link>
          <Link
            to="/como-usar"
            className="inline-flex items-center gap-1.5 text-sm font-medium text-success hover:underline"
          >
            <BookOpen className="size-4" />
            Como usar
          </Link>
        </div>

        <div>
          <h2 className="text-xl font-semibold tracking-tight">Seu perfil</h2>
          <p className="text-sm text-muted-foreground">
            Quem envia as mensagens de prospecção. As copies geradas por IA
            saem assinadas e na sua voz.
          </p>
        </div>

        <PerfilVendedorCard />

        <div>
          <h2 className="text-xl font-semibold tracking-tight">Estratégia de abordagem</h2>
          <p className="text-sm text-muted-foreground">
            O que você vende e como fala. Manda no gerador de mensagens de cada lead.
          </p>
        </div>

        <EstrategiaAbordagemCard abertoInicial />

        <div>
          <h2 className="text-xl font-semibold tracking-tight">Chaves de API</h2>
          <p className="text-sm text-muted-foreground">
            As chaves abaixo são usadas para gerar mensagens por IA. O sistema
            tenta cada provedor na ordem Claude, Gemini, Groq e NVIDIA, e passa
            para o próximo automaticamente se algum falhar ou ficar sem cota.
          </p>
        </div>

        {isLoading || !data ? (
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-[140px]" />
            ))}
          </div>
        ) : (
          <div className="space-y-3">
            {(["anthropic", "gemini", "groq", "nvidia", "pagespeed"] as const).map((provedor) => (
              <ProvedorApiCard
                key={provedor}
                provedor={provedor}
                titulo={TITULOS[provedor]}
                config={data[provedor]}
              />
            ))}
            <p className="text-xs text-muted-foreground">
              A chave do PageSpeed é opcional: adiciona a nota oficial de
              desempenho do Google no diagnóstico em PDF (funciona sem chave
              para uso leve, mas com limites).
            </p>
          </div>
        )}

        <div>
          <h2 className="text-xl font-semibold tracking-tight">Google Places</h2>
          <p className="text-sm text-muted-foreground">
            Chave e consumo da busca de negócios no Google Maps.
          </p>
        </div>

        <FonteMapsCard />

        <div>
          <h2 className="text-xl font-semibold tracking-tight">
            Análise de oportunidade
          </h2>
          <p className="text-sm text-muted-foreground">
            Controle quais leads podem ser analisados pela IA.
          </p>
        </div>

        <AnaliseOportunidadeCard />

        <div>
          <h2 className="text-xl font-semibold tracking-tight">Sons</h2>
          <p className="text-sm text-muted-foreground">
            Controle os sons de feedback do sistema.
          </p>
        </div>

        <SomConfigCard />
      </main>
    </div>
  )
}
