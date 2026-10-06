export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  let response: Response

  try {
    response = await fetch(url, {
      headers: { "Content-Type": "application/json" },
      ...options,
    })
  } catch {
    throw new ApiError(
      "Não foi possível falar com o servidor. Confira se o `py app.py` ainda está rodando.",
      0
    )
  }

  if (!response.ok) {
    let mensagem = `Erro do servidor (${response.status}).`
    try {
      const dados = await response.clone().json()
      if (dados?.erro) mensagem = dados.erro
    } catch {
      // resposta não era JSON, mantém a mensagem genérica
    }
    throw new ApiError(mensagem, response.status)
  }

  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const httpClient = {
  get: <T>(url: string) => request<T>(url),
  post: <T>(url: string, body?: unknown) =>
    request<T>(url, {
      method: "POST",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),
  put: <T>(url: string, body?: unknown) =>
    request<T>(url, {
      method: "PUT",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),
  delete: <T>(url: string) => request<T>(url, { method: "DELETE" }),
}
