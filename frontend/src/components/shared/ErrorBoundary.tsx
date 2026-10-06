import { Component, type ErrorInfo, type ReactNode } from "react"

interface Props {
  children: ReactNode
}

interface State {
  erro: Error | null
}

/**
 * Rede de segurança global: qualquer erro de renderização em qualquer tela
 * vira esta página de erro legível em vez de uma tela branca muda.
 *
 * Sem isso, um crash no React desmonta a árvore inteira e o usuário só vê
 * branco - sem saber o que aconteceu nem como reportar. Com isso, a mensagem
 * do erro fica visível (dá pra tirar print e mandar) e o botão
 * recarrega o app.
 *
 * Estilos inline de propósito: se o crash for no CSS/design system, esta
 * tela ainda renderiza.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { erro: null }

  static getDerivedStateFromError(erro: Error): State {
    return { erro }
  }

  componentDidCatch(erro: Error, info: ErrorInfo) {
    // console é o melhor destino: aparece no F12 e em relatos de bug
    console.error("[PROSPECT WITH MICO] erro de renderização:", erro, info.componentStack)
  }

  render() {
    if (!this.state.erro) return this.props.children

    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 16,
          padding: 24,
          background: "#0f1518",
          color: "#eef2f4",
          fontFamily: "system-ui, sans-serif",
          textAlign: "center",
        }}
      >
        <div style={{ fontSize: 44 }}>😵</div>
        <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0 }}>
          Algo deu errado nesta tela
        </h1>
        <p style={{ maxWidth: 560, margin: 0, color: "#9aa8b2", fontSize: 15, lineHeight: 1.5 }}>
          O PROSPECT WITH MICO encontrou um erro inesperado. Recarregar geralmente
          resolve. Se continuar acontecendo, tire um print desta tela e mande pro
          A mensagem abaixo diz exatamente o que quebrou.
        </p>
        <pre
          style={{
            maxWidth: 640,
            maxHeight: 180,
            overflow: "auto",
            background: "#1a2127",
            border: "1px solid #2b353d",
            borderRadius: 10,
            padding: "12px 16px",
            fontSize: 12,
            color: "#f0b26b",
            textAlign: "left",
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
          }}
        >
          {this.state.erro.message}
          {"\n\n"}
          {this.state.erro.stack?.split("\n").slice(1, 5).join("\n")}
        </pre>
        <button
          type="button"
          onClick={() => window.location.reload()}
          style={{
            padding: "10px 22px",
            borderRadius: 10,
            border: "none",
            background: "#22c55e",
            color: "#04120a",
            fontSize: 15,
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Recarregar o sistema
        </button>
      </div>
    )
  }
}
