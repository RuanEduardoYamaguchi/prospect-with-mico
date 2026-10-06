import { useEffect, useState } from "react"

type Tema = "light" | "dark"

function temaInicial(): Tema {
  const salvo = localStorage.getItem("tema") as Tema | null
  if (salvo === "light" || salvo === "dark") return salvo
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light"
}

export function useTema() {
  const [tema, setTema] = useState<Tema>(temaInicial)

  useEffect(() => {
    document.documentElement.classList.toggle("dark", tema === "dark")
    localStorage.setItem("tema", tema)
  }, [tema])

  const alternar = () => setTema((t) => (t === "dark" ? "light" : "dark"))

  return { tema, alternar }
}
