/**
 * Typed client for the backend HTTP API.
 * Components never call `fetch` directly — they use hooks from `src/hooks/` built on this module.
 */

const API_URL: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export interface ApiErrorBody {
  error: {
    code: string
    message: string
    fields?: { field: string; message: string }[]
  }
}

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly fields: { field: string; message: string }[]

  constructor(status: number, body: ApiErrorBody['error']) {
    super(body.message)
    this.name = 'ApiError'
    this.status = status
    this.code = body.code
    this.fields = body.fields ?? []
  }
}

/** Reads give up after this long; the backend's worst case for a read is ~26 s. */
export const READ_TIMEOUT_MS = 30_000

/** The backend could not be reached at all (no HTTP response). Safe to retry. */
export class NetworkError extends Error {
  constructor(message = 'Cannot reach the server. Check your connection and try again.') {
    super(message)
    this.name = 'NetworkError'
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const method = init?.method ?? 'GET'
  // Only reads time out. Aborting a change would leave its outcome unknown, while the
  // backend still finishes it; changes are bounded by the backend's Keitaro timeouts.
  const signal = method === 'GET' ? AbortSignal.timeout(READ_TIMEOUT_MS) : undefined

  let response: Response
  try {
    response = await fetch(`${API_URL}${path}`, {
      signal,
      ...init,
      headers: { 'Content-Type': 'application/json', ...init?.headers },
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'TimeoutError') {
      throw new ApiError(0, {
        code: 'timeout',
        message: `The server did not respond within ${READ_TIMEOUT_MS / 1000} s. Try again.`,
      })
    }
    throw new NetworkError()
  }

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as ApiErrorBody | null
    throw new ApiError(
      response.status,
      body?.error ?? { code: 'http_error', message: response.statusText || 'Request failed' },
    )
  }

  if (response.status === 204) {
    return undefined as T
  }
  return (await response.json()) as T
}

// --- Types ------------------------------------------------------------------------

export interface HealthResponse {
  status: string
  database: string
}

export interface NamedItem {
  id: number
  name: string
}

export interface Country {
  code: string
  name: string
}

export interface ReferenceData {
  domains: NamedItem[]
  groups: NamedItem[]
  traffic_sources: NamedItem[]
  countries: Country[]
  defaults: {
    domain_id: number | null
    group_id: number | null
    traffic_source_id: number | null
  }
}

export interface Offer {
  id: number
  name: string
  state: string
  countries: string[]
}

export interface CampaignCreateRequest {
  name: string
  geo: string[]
  offer_id: number
  domain_id: number
  group_id: number
  traffic_source_id: number
}

export interface CampaignCreated {
  id: number
  name: string
  alias: string
  geo: string[]
  offer_id: number
  stream_ids: number[]
}

export interface CampaignSummary {
  id: number
  name: string
  alias: string
  state: string
}

export type StreamOfferState = 'active' | 'removed'

export interface StreamOffer {
  offer_id: number
  name: string | null
  state: StreamOfferState
  share: number
  pinned: boolean
  is_new: boolean
  is_dirty: boolean
  published_share: number | null
}

export interface Stream {
  id: number
  name: string
  type: string
  position: number
  editable: boolean
  dirty: boolean
  total_share: number
  push_blocker: string | null
  offers: StreamOffer[]
}

export interface CampaignEditor {
  id: number
  name: string
  alias: string
  fetched_at: string | null
  streams: Stream[]
}

// --- Endpoints --------------------------------------------------------------------

const post = <T>(path: string, body?: unknown, headers?: HeadersInit) =>
  request<T>(path, {
    method: 'POST',
    body: body === undefined ? undefined : JSON.stringify(body),
    headers,
  })

const streamPath = (streamId: number, offerId?: number) =>
  `/api/v1/streams/${streamId}${offerId === undefined ? '' : `/offers/${offerId}`}`

export const api = {
  health: () => request<HealthResponse>('/health'),

  reference: () => request<ReferenceData>('/api/v1/reference'),

  searchOffers: (query: string, limit = 20) =>
    request<Offer[]>(`/api/v1/offers?${new URLSearchParams({ q: query, limit: String(limit) })}`),

  refreshOffers: () => request<{ count: number }>('/api/v1/offers/refresh', { method: 'POST' }),

  /** `idempotencyKey` makes retries safe: the backend replays the first result. */
  createCampaign: (data: CampaignCreateRequest, idempotencyKey: string) =>
    post<CampaignCreated>('/api/v1/campaigns', data, { 'Idempotency-Key': idempotencyKey }),

  // Editor
  listCampaigns: () => request<CampaignSummary[]>('/api/v1/campaigns'),
  getCampaign: (id: number) => request<CampaignEditor>(`/api/v1/campaigns/${id}`),
  fetchCampaign: (id: number) => post<CampaignEditor>(`/api/v1/campaigns/${id}/fetch`),

  addOffer: (streamId: number, offerId: number) =>
    post<Stream>(`${streamPath(streamId)}/offers`, { offer_id: offerId }),
  removeOffer: (streamId: number, offerId: number) =>
    post<Stream>(`${streamPath(streamId, offerId)}/remove`),
  bringBackOffer: (streamId: number, offerId: number) =>
    post<Stream>(`${streamPath(streamId, offerId)}/bring-back`),
  setShare: (streamId: number, offerId: number, share: number) =>
    request<Stream>(`${streamPath(streamId, offerId)}/share`, {
      method: 'PUT',
      body: JSON.stringify({ share }),
    }),
  unpin: (streamId: number, offerId: number) =>
    post<Stream>(`${streamPath(streamId, offerId)}/unpin`),
  pushStream: (streamId: number) => post<Stream>(`${streamPath(streamId)}/push`),
  cancelStream: (streamId: number) => post<Stream>(`${streamPath(streamId)}/cancel`),
}
