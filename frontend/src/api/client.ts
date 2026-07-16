export class ApiError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly details: unknown,
  ) {
    super(message)
  }
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  const responseText = await response.text()
  const body = responseText ? JSON.parse(responseText) : undefined

  if (!response.ok) {
    const error = body?.error
    throw new ApiError(
      error?.code ?? `http_${response.status}`,
      error?.message ?? `HTTP ${response.status}`,
      error?.details,
    )
  }

  return body as T
}
