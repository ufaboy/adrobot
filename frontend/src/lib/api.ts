/**
 * Typed client for the backend HTTP API.
 * Components never call `fetch` directly — they use hooks from `src/hooks/` built on this module.
 */

const API_URL: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export interface ApiErrorBody {
  error: { code: string; message: string }
}

export class ApiError extends Error {
  readonly status: number
  readonly code: string

  constructor(status: number, code: string, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as ApiErrorBody | null
    throw new ApiError(
      response.status,
      body?.error.code ?? 'http_error',
      body?.error.message ?? response.statusText,
    )
  }

  if (response.status === 204) {
    return undefined as T
  }
  return (await response.json()) as T
}

export interface HealthResponse {
  status: string
  database: string
}

export const api = {
  health: () => request<HealthResponse>('/health'),
}
