export function pedirPermissaoNotificacao() {
  if (!("Notification" in window)) return
  if (Notification.permission === "default") {
    Notification.requestPermission()
  }
}

export function notificar(titulo: string, corpo: string) {
  if (!("Notification" in window)) return
  if (Notification.permission !== "granted") return

  const notificacao = new Notification(titulo, {
    body: corpo,
    icon: "/favicon.svg",
  })

  notificacao.onclick = () => {
    window.focus()
    notificacao.close()
  }
}
