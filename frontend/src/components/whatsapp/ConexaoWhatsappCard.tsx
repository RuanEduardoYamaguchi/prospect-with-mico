import { useState } from "react"
import { CheckCircle2, Loader2, QrCode, Smartphone, TriangleAlert } from "lucide-react"
import { AvisoNumeroOficial } from "@/components/whatsapp/AvisoNumeroOficial"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"
import {
  useConectarWhatsapp,
  useDesconectarWhatsapp,
  useEstadoWhatsapp,
} from "@/hooks/useWhatsapp"

export function ConexaoWhatsappCard() {
  const { data: estado, isLoading } = useEstadoWhatsapp()
  const conectar = useConectarWhatsapp()
  const desconectar = useDesconectarWhatsapp()
  const [qrBase64, setQrBase64] = useState<string | null>(null)

  const conectado = Boolean(estado?.conectado)

  // assim que a conexão pega, o QR não serve mais pra nada
  if (conectado && qrBase64) setQrBase64(null)

  const handleConectar = () => {
    conectar.mutate(undefined, {
      onSuccess: (resposta) => setQrBase64(resposta.qr_base64),
    })
  }

  if (isLoading || !estado) {
    return <Skeleton className="h-[140px] rounded-xl" />
  }

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Smartphone className="size-4 text-muted-foreground" />
          <h3 className="font-medium">Conexão do WhatsApp</h3>
        </div>

        {!estado.evolution_ok ? (
          <span className="inline-flex items-center gap-1 rounded-full bg-destructive/15 px-2 py-0.5 text-xs font-medium text-destructive">
            <TriangleAlert className="size-3.5" />
            Evolution indisponível
          </span>
        ) : conectado ? (
          <span className="inline-flex items-center gap-1 rounded-full bg-success/15 px-2 py-0.5 text-xs font-medium text-success">
            <CheckCircle2 className="size-3.5" />
            Conectado{estado.numero ? ` · ${estado.numero}` : ""}
          </span>
        ) : estado.estado === "connecting" ? (
          <span className="inline-flex items-center gap-1 rounded-full bg-warning/15 px-2 py-0.5 text-xs font-medium text-warning">
            <Loader2 className="size-3.5 animate-spin" />
            Conectando...
          </span>
        ) : (
          <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
            Desconectado
          </span>
        )}
      </div>

      {conectado && estado.numero_oficial && <AvisoNumeroOficial />}
      {conectado && estado.oficial_liberado && <AvisoNumeroOficial liberado />}

      {!conectado && (
        <p className="text-sm text-muted-foreground">
          Leia o QR code com o celular do chip de disparo: WhatsApp › Aparelhos
          conectados › Conectar aparelho.
        </p>
      )}

      {qrBase64 && !conectado && (
        <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border bg-muted/30 p-4">
          <img src={qrBase64} alt="QR code de conexão do WhatsApp" className="size-48" />
          <p className="text-xs text-muted-foreground">
            Aguardando leitura - atualiza sozinho assim que conectar.
          </p>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleConectar}
            disabled={conectar.isPending}
          >
            <QrCode className="size-4" />
            {conectar.isPending ? "Gerando..." : "Gerar novo QR code"}
          </Button>
        </div>
      )}

      <div>
        {conectado ? (
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="outline" className="text-destructive hover:bg-destructive/10">
                Desconectar
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Desconectar o WhatsApp?</AlertDialogTitle>
                <AlertDialogDescription>
                  Campanhas em andamento param de enviar e o envio manual pelo
                  cockpit fica indisponível até conectar de novo.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancelar</AlertDialogCancel>
                <AlertDialogAction onClick={() => desconectar.mutate()}>
                  Desconectar
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        ) : (
          <Button
            onClick={handleConectar}
            disabled={conectar.isPending || !estado.evolution_ok}
            className={cn(conectar.isPending && "opacity-80")}
          >
            <QrCode className="size-4" />
            {conectar.isPending ? "Gerando QR..." : "Conectar WhatsApp"}
          </Button>
        )}
      </div>
    </div>
  )
}
