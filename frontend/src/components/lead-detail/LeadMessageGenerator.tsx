import { useEffect, useState } from "react"
import { Camera, MessageCircleReply, Send, Sparkles } from "lucide-react"
import { Link } from "react-router-dom"
import { toast } from "sonner"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { useClipboard } from "@/hooks/useClipboard"
import { useAquecimento, useEstadoWhatsapp } from "@/hooks/useWhatsapp"
import { ajustarSaudacao } from "@/lib/saudacao"
import { formatarTempoRelativo } from "@/lib/formatters"
import { linkWhatsappComMensagem } from "@/services/tarefasService"
import { conversaService } from "@/services/conversaService"
import type { UseMutationResult } from "@tanstack/react-query"
import type { AbordagemContato, GerarMensagemResposta, Lead } from "@/types/lead"
import type { EnviarMensagemResposta } from "@/types/whatsapp"

interface LeadMessageGeneratorProps {
  lead: Lead
  gerarMensagem: UseMutationResult<
    GerarMensagemResposta,
    Error,
    {
      forcarNova: boolean
      tipo?: "contato" | "followup"
      abordagem?: AbordagemContato
    },
    unknown
  >
  marcarFollowupEnviado: UseMutationResult<
    unknown,
    Error,
    {
      followUpsEnviadosAnterior: number
      ultimoFollowupEmAnterior: string | null
      proximoFollowupAnterior: string | null
    },
    unknown
  >
  enviarWhatsapp: UseMutationResult<EnviarMensagemResposta, Error, string | { texto: string; followup?: boolean }, unknown>
  children?: React.ReactNode
}

export function LeadMessageGenerator({
  lead,
  gerarMensagem,
  marcarFollowupEnviado,
  enviarWhatsapp,
  children,
}: LeadMessageGeneratorProps) {
  const [mensagem, setMensagem] = useState(lead.mensagem_gerada ?? "")

  useEffect(() => {
    setMensagem(lead.mensagem_gerada ?? "")
  }, [lead.place_id, lead.mensagem_gerada])

  const { copiado, copiar } = useClipboard()
  const {
    copiado: numeroCopiado,
    copiar: copiarNumero,
  } = useClipboard()
  const { data: estadoWhatsapp } = useEstadoWhatsapp()
  const { data: aquecimento } = useAquecimento()
  const restantesHoje = aquecimento?.restantes_hoje ?? 0

  const handleGerar = (
    tipo: "contato" | "followup",
    abordagem: AbordagemContato = "direta"
  ) => {
    // trocar de abordagem sempre gera de novo: a mensagem em cache é a da
    // abordagem anterior, e devolvê-la faria o botão parecer quebrado
    const jaTinhaMensagem = mensagem.trim().length > 0
    gerarMensagem.mutate(
      { forcarNova: jaTinhaMensagem, tipo, abordagem },
      {
        onSuccess: (resposta) => {
          setMensagem(resposta.mensagem)
          if (resposta.avisos?.length) {
            toast.warning(
              `${resposta.avisos.join(" ")} (usado: ${resposta.provedor ?? "?"})`
            )
          } else {
            toast.success("Mensagem gerada com sucesso.")
          }
        },
      }
    )
  }

  const conectado = Boolean(estadoWhatsapp?.conectado)
  const semMensagem = !mensagem.trim()
  const semTeto = restantesHoje <= 0
  const motivoBloqueio = semMensagem
    ? "Escreva ou gere uma mensagem pra enviar."
    : !conectado
      ? "WhatsApp desconectado. Conecte na página WhatsApp."
      : semTeto
        ? "Teto de envios de hoje atingido."
        : null
  const linkClasse =
    "text-xs text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"

  return (
    <div className="flex flex-1 flex-col gap-2">
      <Label>Escreva a sua mensagem ou gere com IA</Label>
      <Textarea
        value={mensagem}
        onChange={(e) => setMensagem(e.target.value)}
        placeholder="Escreva aqui ou use um dos botões de gerar com IA"
        className="min-h-[200px] flex-1 resize-none"
      />

      <div className="flex flex-wrap items-center gap-1.5">
        <span className="text-xs text-muted-foreground">Gerar com IA:</span>
        <Button
          size="sm"
          variant="outline"
          className="h-7 px-2 text-xs"
          onClick={() => handleGerar("contato")}
          disabled={gerarMensagem.isPending}
        >
          <Sparkles className="size-3.5" />
          {gerarMensagem.isPending ? "Gerando..." : "Contato"}
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="h-7 px-2 text-xs"
          onClick={() => handleGerar("contato", "print")}
          disabled={gerarMensagem.isPending}
          title="Abertura curta que não vende: pede pra falar com o responsável e oferece um print."
        >
          <Camera className="size-3.5" />
          Pedido de print
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="h-7 px-2 text-xs"
          onClick={() => handleGerar("followup")}
          disabled={gerarMensagem.isPending}
        >
          <MessageCircleReply className="size-3.5" />
          Follow-up
        </Button>
      </div>

      <Button
        size="lg"
        className="mt-1 w-full bg-success text-white hover:bg-success/90"
        // lead já contatado: é retorno, não primeiro contato repetido
        onClick={() => enviarWhatsapp.mutate({ texto: ajustarSaudacao(mensagem), followup: lead.status !== "novo" })}
        disabled={enviarWhatsapp.isPending || motivoBloqueio !== null}
      >
        <Send className="size-4" />
        {enviarWhatsapp.isPending ? "Enviando..." : "Enviar pelo WhatsApp"}
      </Button>
      {motivoBloqueio && (
        <p className="text-xs text-muted-foreground">
          {motivoBloqueio}
          {!conectado && !semMensagem && (
            <>
              {" "}
              <Link to="/whatsapp" className="underline">
                Abrir WhatsApp
              </Link>
            </>
          )}
        </p>
      )}
      {conectado && (
        <p className="text-xs text-muted-foreground">
          {restantesHoje > 0
            ? `${restantesHoje} envio(s) restante(s) hoje no aquecimento do chip.`
            : "Teto de hoje do aquecimento esgotado, o envio direto volta amanhã."}
        </p>
      )}

      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <button type="button" className={linkClasse} onClick={() => copiar(ajustarSaudacao(mensagem))}>
          {copiado ? "Copiado!" : "Copiar"}
        </button>
        <button type="button" className={linkClasse} onClick={() => copiarNumero(lead.telefone ?? "")}>
          {numeroCopiado ? "Copiado!" : "Copiar número"}
        </button>
        {lead.whatsapp_link && (
          <button
            type="button"
            className={linkClasse}
            onClick={() => {
              // avisa de quem é a conversa antes da janela abrir, pro cockpit
              // vincular as mensagens capturadas ao lead certo
              conversaService.registrarLeadAtivo("maps", lead.place_id).catch(() => {})
              window.open(
                linkWhatsappComMensagem(lead.whatsapp_link!, mensagem || null),
                "_blank"
              )
            }}
          >
            Abrir no WhatsApp Web
          </button>
        )}
      </div>

      <div className="mt-2 flex flex-wrap items-center justify-between gap-2 border-t border-border pt-3">
        <div className="flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            variant="secondary"
            onClick={() =>
              marcarFollowupEnviado.mutate({
                followUpsEnviadosAnterior: lead.follow_ups_enviados,
                ultimoFollowupEmAnterior: lead.ultimo_followup_em,
                proximoFollowupAnterior: lead.proximo_followup,
              })
            }
            disabled={marcarFollowupEnviado.isPending}
          >
            Marquei follow-up
            {lead.follow_ups_enviados > 0 && ` (${lead.follow_ups_enviados})`}
          </Button>
          {lead.ultimo_followup_em && lead.follow_ups_enviados > 0 && (
            <span className="text-xs text-muted-foreground">
              último em {formatarTempoRelativo(lead.ultimo_followup_em)}
            </span>
          )}
        </div>
        {children}
      </div>
    </div>
  )
}
