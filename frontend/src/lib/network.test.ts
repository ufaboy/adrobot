import { afterEach, describe, expect, it, vi } from 'vitest'

import { api, ApiError, NetworkError } from '@/lib/api'
import { shouldRetryQuery } from '@/lib/query-retry'

const okJson = (body: unknown) =>
  new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } })

describe('API client network handling', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('turns an unreachable backend into a NetworkError', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    await expect(api.listCampaigns()).rejects.toBeInstanceOf(NetworkError)
  })

  it('turns a read timeout into an ApiError with code "timeout"', async () => {
    const timeout = new DOMException('signal timed out', 'TimeoutError')
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(timeout))

    const error = await api.listCampaigns().catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).code).toBe('timeout')
  })

  it('puts a timeout on reads but never on changes', async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(okJson([])))
    vi.stubGlobal('fetch', fetchMock)

    await api.listCampaigns()
    await api.pushStream(7)

    const [, read] = fetchMock.mock.calls[0] as [string, RequestInit]
    const [, change] = fetchMock.mock.calls[1] as [string, RequestInit]
    expect(read.signal).toBeInstanceOf(AbortSignal)
    expect(change.signal).toBeUndefined()
  })

  it('sends the idempotency key with campaign creation', async () => {
    const fetchMock = vi.fn().mockResolvedValue(okJson({}))
    vi.stubGlobal('fetch', fetchMock)

    await api.createCampaign(
      { name: 'x', geo: ['AU'], offer_id: 1, domain_id: 1, group_id: 1, traffic_source_id: 1 },
      'key-1',
    )

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(new Headers(init.headers).get('Idempotency-Key')).toBe('key-1')
  })
})

describe('shouldRetryQuery', () => {
  it('retries a network error once', () => {
    expect(shouldRetryQuery(0, new NetworkError())).toBe(true)
    expect(shouldRetryQuery(1, new NetworkError())).toBe(false)
  })

  it('does not retry error responses from the backend', () => {
    const keitaroDown = new ApiError(503, { code: 'keitaro_unavailable', message: 'down' })
    expect(shouldRetryQuery(0, keitaroDown)).toBe(false)
  })
})
