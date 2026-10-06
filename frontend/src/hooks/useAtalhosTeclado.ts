import { useEffect } from "react"

interface AtalhosTecladoOptions {
  onFocarBusca: () => void
  onNovaBusca: () => void
}

function estaDigitando(alvo: EventTarget | null): boolean {
  if (!(alvo instanceof HTMLElement)) return false
  const tag = alvo.tagName
  return tag === "INPUT" || tag === "TEXTAREA" || alvo.isContentEditable
}

export function useAtalhosTeclado({
  onFocarBusca,
  onNovaBusca,
}: AtalhosTecladoOptions) {
  useEffect(() => {
    function handler(e: KeyboardEvent) {
      const jaDigitando = estaDigitando(e.target)

      if (e.key === "/" && !jaDigitando) {
        e.preventDefault()
        onFocarBusca()
        return
      }

      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault()
        onFocarBusca()
        return
      }

      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "b" && !jaDigitando) {
        e.preventDefault()
        onNovaBusca()
      }
    }

    window.addEventListener("keydown", handler)
    return () => window.removeEventListener("keydown", handler)
  }, [onFocarBusca, onNovaBusca])
}
