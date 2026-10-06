import { Loader2 } from "lucide-react"
import { motion } from "framer-motion"

interface BuscaFloatingIndicatorProps {
  mensagem: string
  onClick: () => void
}

export function BuscaFloatingIndicator({
  mensagem,
  onClick,
}: BuscaFloatingIndicatorProps) {
  return (
    <motion.button
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      onClick={onClick}
      className="fixed bottom-5 right-5 z-30 flex items-center gap-2 rounded-full border border-border bg-card px-4 py-2.5 text-sm shadow-lg hover:bg-accent/50"
    >
      <Loader2 className="size-4 animate-spin text-primary" />
      <span className="max-w-[220px] truncate">{mensagem}</span>
    </motion.button>
  )
}
