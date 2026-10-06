import { TriangleAlert } from "lucide-react"

/** Aparece quando o chip conectado é o número oficial do negócio (NUMERO_OFICIAL
 * no backend/.env).
 * - bloqueado (padrão): o backend recusa campanha; o aviso explica por quê.
 * - liberado (PERMITIR_CAMPANHA_NO_OFICIAL no .env): campanha roda, com teto
 *   de 20 envios por dia; o aviso lembra do risco. */
export function AvisoNumeroOficial({ liberado = false }: { liberado?: boolean }) {
  if (liberado) {
    return (
      <div className="flex gap-2 rounded-lg border border-warning/40 bg-warning/10 p-3 text-sm">
        <TriangleAlert className="mt-0.5 size-4 shrink-0 text-warning" />
        <div className="space-y-1">
          <p className="font-medium text-warning">Disparando pelo número oficial</p>
          <p className="text-muted-foreground">
            Liberado por você no .env, com teto de 20 envios por dia. Se o número
            cair por denúncia, cai junto o canal com os seus clientes. Troque pelo
            chip de prospecção assim que tiver um.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex gap-2 rounded-lg border border-destructive/40 bg-destructive/10 p-3 text-sm">
      <TriangleAlert className="mt-0.5 size-4 shrink-0 text-destructive" />
      <div className="space-y-1">
        <p className="font-medium text-destructive">Este é o seu número oficial</p>
        <p className="text-muted-foreground">
          Campanha fica bloqueada nele: se o número cair por denúncia, cai junto o
          canal com os seus clientes. Envio individual pelo lead continua liberado.
          Pra disparar, desconecte e leia o QR code com um chip de prospecção.
        </p>
      </div>
    </div>
  )
}
