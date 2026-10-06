import { useRef, useState } from "react"
import { Upload } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { useImportarKaptar } from "@/hooks/useImportar"
import type { ImportarKaptarResposta } from "@/types/whatsapp"

interface ImportarKaptarDialogProps {
  aberto: boolean
  onFechar: () => void
}

export function ImportarKaptarDialog({ aberto, onFechar }: ImportarKaptarDialogProps) {
  const [conteudo, setConteudo] = useState("")
  const [nomeArquivo, setNomeArquivo] = useState("")
  const [nichoPadrao, setNichoPadrao] = useState("")
  const [cidadePadrao, setCidadePadrao] = useState("")
  const [resultado, setResultado] = useState<ImportarKaptarResposta | null>(null)
  const inputArquivoRef = useRef<HTMLInputElement>(null)
  const importar = useImportarKaptar()

  const handleArquivo = (arquivo: File | undefined) => {
    if (!arquivo) return
    setNomeArquivo(arquivo.name)
    const leitor = new FileReader()
    leitor.onload = () => setConteudo(String(leitor.result ?? ""))
    leitor.readAsText(arquivo)
  }

  const handleImportar = () => {
    if (!conteudo.trim()) return
    importar.mutate(
      {
        conteudo,
        nichoPadrao: nichoPadrao.trim() || undefined,
        cidadePadrao: cidadePadrao.trim() || undefined,
      },
      { onSuccess: setResultado }
    )
  }

  const handleFechar = () => {
    setConteudo("")
    setNomeArquivo("")
    setNichoPadrao("")
    setCidadePadrao("")
    setResultado(null)
    onFechar()
  }

  return (
    <Dialog open={aberto} onOpenChange={(open) => !open && handleFechar()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Upload className="size-4" />
            Importar CSV do Kaptar
          </DialogTitle>
          <DialogDescription>
            Solte o CSV exportado do Kaptar ou cole a lista direto. Os dois
            formatos do Kaptar funcionam.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => inputArquivoRef.current?.click()}
            >
              Escolher CSV
            </Button>
            <input
              ref={inputArquivoRef}
              type="file"
              accept=".csv,.tsv,.txt"
              hidden
              onChange={(e) => handleArquivo(e.target.files?.[0])}
            />
            {nomeArquivo && (
              <span className="truncate text-xs text-muted-foreground">{nomeArquivo}</span>
            )}
          </div>

          <Textarea
            value={conteudo}
            onChange={(e) => setConteudo(e.target.value)}
            rows={6}
            placeholder="Nome;Nicho;Telefone;WhatsApp provável;Site;Tem site;..."
            className="font-mono text-xs"
          />

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label>Nicho padrão (opcional)</Label>
              <Input
                value={nichoPadrao}
                onChange={(e) => setNichoPadrao(e.target.value)}
                placeholder="Se a lista não tiver a coluna"
              />
            </div>
            <div className="space-y-1.5">
              <Label>Cidade padrão (opcional)</Label>
              <Input
                value={cidadePadrao}
                onChange={(e) => setCidadePadrao(e.target.value)}
                placeholder="Se a lista não tiver a coluna"
              />
            </div>
          </div>

          {resultado && (
            <div className="rounded-lg bg-success/10 p-3 text-sm text-success">
              {resultado.importados} lead(s) novo(s), {resultado.atualizados}{" "}
              atualizado(s).
              {Object.keys(resultado.descartados).length > 0 && (
                <p className="mt-1 text-xs text-muted-foreground">
                  Descartados:{" "}
                  {Object.entries(resultado.descartados)
                    .map(([motivo, n]) => `${motivo} (${n})`)
                    .join(", ")}
                </p>
              )}
            </div>
          )}

          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={handleFechar}>
              {resultado ? "Fechar" : "Cancelar"}
            </Button>
            <Button
              onClick={handleImportar}
              disabled={!conteudo.trim() || importar.isPending}
            >
              {importar.isPending ? "Importando..." : "Importar"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
