import { useEffect, useRef } from "react"

export function useIntersectionObserver(aoInterseccionar: () => void, ativo: boolean) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ativo) return
    const elemento = ref.current
    if (!elemento) return

    const observer = new IntersectionObserver(
      (entradas) => {
        if (entradas[0]?.isIntersecting) aoInterseccionar()
      },
      { rootMargin: "200px" }
    )
    observer.observe(elemento)
    return () => observer.disconnect()
  }, [aoInterseccionar, ativo])

  return ref
}
