import { motion } from "framer-motion"
import { Trash2, X } from "lucide-react"
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useBulkMutations } from "@/hooks/useBulkMutations"
import { LABEL_STATUS } from "@/lib/constants"
import { STATUS_VALIDOS, type StatusLead } from "@/types/lead"

interface BulkActionsBarProps {
  placeIdsSelecionados: string[]
  onLimparSelecao: () => void
  modoIgnorados?: boolean
}

export function BulkActionsBar({
  placeIdsSelecionados,
  onLimparSelecao,
  modoIgnorados = false,
}: BulkActionsBarProps) {
  const { atualizarStatusEmLote, ignorarEmLote, excluirEmLoteDefinitivamente } =
    useBulkMutations()

  const handleMudarStatus = (status: StatusLead) => {
    atualizarStatusEmLote.mutate(
      { placeIds: placeIdsSelecionados, status },
      { onSuccess: onLimparSelecao }
    )
  }

  const handleExcluir = () => {
    if (modoIgnorados) {
      excluirEmLoteDefinitivamente.mutate(placeIdsSelecionados, {
        onSuccess: onLimparSelecao,
      })
    } else {
      ignorarEmLote.mutate(placeIdsSelecionados, { onSuccess: onLimparSelecao })
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }}
      className="fixed bottom-5 left-1/2 z-30 flex -translate-x-1/2 items-center gap-3 rounded-full border border-border bg-card px-4 py-2.5 shadow-lg"
    >
      <span className="text-sm font-medium">
        {placeIdsSelecionados.length} selecionado(s)
      </span>

      {!modoIgnorados && (
        <Select onValueChange={(v) => handleMudarStatus(v as StatusLead)}>
          <SelectTrigger className="h-8 w-[160px]">
            <SelectValue placeholder="Mudar status" />
          </SelectTrigger>
          <SelectContent>
            {STATUS_VALIDOS.filter((s) => s !== "ignorado").map((status) => (
              <SelectItem key={status} value={status}>
                {LABEL_STATUS[status]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}

      <AlertDialog>
        <AlertDialogTrigger asChild>
          <Button size="sm" variant="outline" className="text-destructive hover:bg-destructive/10">
            <Trash2 className="size-4" />
            {modoIgnorados ? "Excluir definitivamente" : "Excluir"}
          </Button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {modoIgnorados
                ? `Excluir ${placeIdsSelecionados.length} lead(s) definitivamente?`
                : `Excluir ${placeIdsSelecionados.length} lead(s)?`}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {modoIgnorados
                ? "Isso apaga esses leads de vez do banco de dados. Não tem como desfazer, e se a mesma busca rodar de novo no futuro, eles podem voltar a aparecer como leads novos."
                : "Eles não vão mais aparecer na sua lista, nem em buscas futuras do mesmo nicho/cidade."}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={handleExcluir}>
              {modoIgnorados ? "Excluir definitivamente" : "Excluir"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <Button size="icon" variant="ghost" className="size-8" onClick={onLimparSelecao}>
        <X className="size-4" />
      </Button>
    </motion.div>
  )
}
