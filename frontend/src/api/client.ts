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
  const body = await response.json()

  if (!response.ok) {
    throw new ApiError(body.error.code, body.error.message, body.error.details)
  }

  return body as T
}
