import { Trash2 } from "lucide-react"
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

interface DeleteLeadButtonProps {
  nomeLead: string
  onConfirmar: () => void
  definitivo?: boolean
}

export function DeleteLeadButton({
  nomeLead,
  onConfirmar,
  definitivo = false,
}: DeleteLeadButtonProps) {
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button variant="outline" className="w-full text-destructive hover:bg-destructive/10">
          <Trash2 className="size-4" />
          {definitivo ? "Excluir definitivamente" : "Excluir este lead"}
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>
            {definitivo
              ? `Excluir "${nomeLead}" definitivamente?`
              : `Excluir "${nomeLead}"?`}
          </AlertDialogTitle>
          <AlertDialogDescription>
            {definitivo
              ? "Isso apaga o lead de vez do banco de dados. Não tem como desfazer, e se a mesma busca rodar de novo no futuro, ele pode voltar a aparecer como lead novo."
              : "Ele não vai mais aparecer na sua lista, nem em buscas futuras do mesmo nicho/cidade."}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancelar</AlertDialogCancel>
          <AlertDialogAction onClick={onConfirmar}>
            {definitivo ? "Excluir definitivamente" : "Excluir"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
