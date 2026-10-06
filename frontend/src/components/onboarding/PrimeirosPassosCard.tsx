import { useState } from "react"
import { Link } from "react-router-dom"
import { ChevronRight, Circle, CircleCheck, Rocket, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useOnboarding } from "@/hooks/useOnboarding"
import { useEstadoWhatsapp } from "@/hooks/useWhatsapp"
import { cn } from "@/lib/utils"

type Nivel = "obrigatorio" | "recomendado" | "opcional"

interface Passo {
  chave: string
  titulo: string
  descricao: string
  nivel: Nivel
  feito: boolean
  rota: string
  acao: string
}

const ROTULO_NIVEL: Record<Nivel, string> = {
  obrigatorio: "obrigatório",
  recomendado: "recomendado",
  opcional: "opcional",
}

const CHAVE_DISPENSADO = "primeiros-passos-dispensado"

function jaDispensou(): boolean {
  try {
    return localStorage.getItem(CHAVE_DISPENSADO) === "1"
  } catch {
    return false
  }
}

function guardarDispensa() {
  try {
    localStorage.setItem(CHAVE_DISPENSADO, "1")
  } catch {
    // sem storage disponível: o card só some nesta visita
  }
}

interface PrimeirosPassosCardProps {
  /** Na página "Como usar" o checklist fica sempre à vista. No painel, some
   * quando o essencial está pronto ou quando a pessoa dispensa. */
  sempreVisivel?: boolean
}

/** Checklist de primeiro uso. Lê o estado real da instalação (chaves, perfil,
 * estratégia, leads, WhatsApp), então marca sozinho conforme a pessoa avança. */
export function PrimeirosPassosCard({ sempreVisivel = false }: PrimeirosPassosCardProps) {
  const { data } = useOnboarding()
  const { data: whatsapp } = useEstadoWhatsapp()
  const [dispensado, setDispensado] = useState(jaDispensou)

  if (!data) return null

  const passos: Passo[] = [
    {
      chave: "ia",
      titulo: "Cole uma chave de IA",
      descricao:
        "É a IA que escreve as mensagens. Gemini e Groq têm plano gratuito; Claude é pago por uso.",
      nivel: "obrigatorio",
      feito: data.ia_configurada,
      rota: "/configuracoes",
      acao: "Abrir configurações",
    },
    {
      chave: "places",
      titulo: "Cole a chave do Google Places",
      descricao:
        "É ela que acha os negócios no Google Maps. Tem cota gratuita mensal e o sistema respeita um teto.",
      nivel: "obrigatorio",
      feito: data.places_configurada,
      rota: "/configuracoes",
      acao: "Abrir configurações",
    },
    {
      chave: "perfil",
      titulo: "Preencha o seu perfil",
      descricao: "Seu nome e o que você faz. As mensagens saem assinadas por você, na sua voz.",
      nivel: "recomendado",
      feito: data.perfil_preenchido,
      rota: "/configuracoes",
      acao: "Abrir configurações",
    },
    {
      chave: "estrategia",
      titulo: "Escreva a sua estratégia de abordagem",
      descricao:
        "Diga o que você vende e como fala. Tem um modelo pronto: é só trocar os trechos [PREENCHER].",
      nivel: "recomendado",
      feito: data.estrategia_personalizada,
      rota: "/configuracoes",
      acao: "Abrir configurações",
    },
    {
      chave: "busca",
      titulo: "Faça a sua primeira busca",
      descricao: "Em Leads, clique em Nova busca e escolha um nicho e uma cidade.",
      nivel: "obrigatorio",
      feito: data.total_leads > 0,
      rota: "/leads",
      acao: "Ir para Leads",
    },
    {
      chave: "whatsapp",
      titulo: "Conecte o WhatsApp",
      descricao:
        "Leia o QR code com um chip de prospecção. Sem isso você usa o sistema normalmente e copia as mensagens.",
      nivel: "opcional",
      feito: Boolean(whatsapp?.conectado),
      rota: "/whatsapp",
      acao: "Abrir WhatsApp",
    },
  ]

  const essencialPronto = passos.filter((p) => p.nivel === "obrigatorio").every((p) => p.feito)
  if (!sempreVisivel && (dispensado || essencialPronto)) return null

  const feitos = passos.filter((p) => p.feito).length

  const dispensar = () => {
    guardarDispensa()
    setDispensado(true)
  }

  return (
    <section className="rounded-2xl border border-border bg-card p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <Rocket className="size-5" />
          </div>
          <div>
            <h2 className="text-lg font-semibold tracking-tight">Primeiros passos</h2>
            <p className="text-sm text-muted-foreground">
              {feitos} de {passos.length} prontos. Faça na ordem; leva uns 10 minutos.
            </p>
          </div>
        </div>
        {!sempreVisivel && (
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={dispensar}
            aria-label="Dispensar primeiros passos"
            title="Dispensar (continua em Como usar)"
          >
            <X className="size-4" />
          </Button>
        )}
      </div>

      <div
        className="mt-4 h-1.5 overflow-hidden rounded-full bg-muted"
        role="progressbar"
        aria-label="Progresso dos primeiros passos"
        aria-valuenow={feitos}
        aria-valuemin={0}
        aria-valuemax={passos.length}
      >
        <div
          className="h-full rounded-full bg-success transition-all"
          style={{ width: `${(feitos / passos.length) * 100}%` }}
        />
      </div>

      <ol className="mt-4 divide-y divide-border">
        {passos.map((passo) => (
          <li key={passo.chave} className="flex items-start gap-3 py-3">
            {passo.feito ? (
              <CircleCheck aria-hidden className="mt-0.5 size-5 shrink-0 text-success" />
            ) : (
              <Circle aria-hidden className="mt-0.5 size-5 shrink-0 text-muted-foreground/60" />
            )}
            <div className="min-w-0 flex-1">
              <p className="flex flex-wrap items-center gap-2 text-sm font-medium">
                <span className={cn(passo.feito && "text-muted-foreground line-through")}>
                  {passo.titulo}
                  <span className="sr-only">{passo.feito ? " (feito)" : " (pendente)"}</span>
                </span>
                {!passo.feito && (
                  <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                    {ROTULO_NIVEL[passo.nivel]}
                  </span>
                )}
              </p>
              {!passo.feito && (
                <p className="mt-0.5 text-xs text-muted-foreground">{passo.descricao}</p>
              )}
            </div>
            {!passo.feito && (
              <Button asChild variant="outline" size="sm" className="shrink-0">
                <Link to={passo.rota}>
                  {passo.acao}
                  <ChevronRight className="size-4" />
                </Link>
              </Button>
            )}
          </li>
        ))}
      </ol>
    </section>
  )
}
