import { Link, NavLink } from "react-router-dom"
import { LayoutDashboard, MapPin, MessageCircle, Plus, Send, Settings, Zap } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { ThemeToggle } from "@/components/layout/ThemeToggle"
import { useAutoresposta, useEstadoWhatsapp } from "@/hooks/useWhatsapp"

interface HeaderProps {
  onNovaBusca?: () => void
}

function ItemNav({
  to,
  end,
  icone,
  ariaLabel,
  children,
  indicador,
}: {
  to: string
  end?: boolean
  icone: React.ReactNode
  ariaLabel?: string
  children?: React.ReactNode
  /** Bolinha de status (ex.: conexão do WhatsApp) sobreposta ao ícone */
  indicador?: React.ReactNode
}) {
  return (
    <NavLink
      to={to}
      end={end}
      aria-label={ariaLabel}
      className={({ isActive }) =>
        cn(
          "relative inline-flex h-8 items-center gap-1.5 whitespace-nowrap rounded-md px-2.5 text-sm font-medium transition-colors",
          isActive
            ? "bg-accent text-foreground"
            : "text-muted-foreground hover:bg-accent/60 hover:text-foreground"
        )
      }
    >
      <span className="relative inline-flex">
        {icone}
        {indicador}
      </span>
      {/* com 5 itens os rótulos cabem a partir de md */}
      {children && <span className="hidden md:inline">{children}</span>}
    </NavLink>
  )
}

export function Header({ onNovaBusca }: HeaderProps) {
  const { data: estadoWhatsapp } = useEstadoWhatsapp()
  const { data: autoresposta } = useAutoresposta()

  return (
    <header className="sticky top-0 z-20 border-b border-border/60 bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
        <Link to="/" className="flex shrink-0 items-center gap-2">
          <img src="/logo-icon.svg" alt="" className="size-9" />
          <h1 className="flex flex-col leading-none">
            <span className="text-lg font-semibold tracking-tight">PROSPECT</span>
            <span className="mt-0.5 text-[10px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
              with Mico
            </span>
          </h1>
        </Link>

        <nav className="flex items-center gap-0.5">
          <ItemNav to="/" end icone={<LayoutDashboard className="size-4" />}>
            Painel
          </ItemNav>
          <ItemNav to="/hoje" icone={<Zap className="size-4" />}>
            Hoje
          </ItemNav>
          <ItemNav to="/leads" icone={<MapPin className="size-4" />}>
            Leads
          </ItemNav>
          <ItemNav to="/campanhas" icone={<Send className="size-4" />}>
            Campanhas
          </ItemNav>
          <ItemNav
            to="/whatsapp"
            icone={<MessageCircle className="size-4" />}
            indicador={
              <span
                className={cn(
                  "absolute -right-0.5 -top-0.5 size-1.5 rounded-full ring-1 ring-background",
                  estadoWhatsapp?.conectado ? "bg-success" : "bg-destructive"
                )}
              />
            }
          >
            WhatsApp
          </ItemNav>
          {autoresposta?.ativa && (
            <Link
              to="/whatsapp"
              title="Resposta automática da IA ligada. Clique pra mudar."
              className="rounded-full bg-success/15 px-1.5 py-0.5 text-[10px] font-semibold text-success"
            >
              IA
            </Link>
          )}
          {onNovaBusca && (
            <Button size="sm" onClick={onNovaBusca}>
              <Plus className="size-4" />
              <span className="hidden sm:inline">Nova busca</span>
            </Button>
          )}
          <ItemNav
            to="/configuracoes"
            icone={<Settings className="size-4" />}
            ariaLabel="Configurações"
          />
          <ThemeToggle />
        </nav>
      </div>
    </header>
  )
}
