import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { useCreateCampaign } from '@/hooks/use-campaign-creator'
import { api, ApiError, type CampaignCreated, type CampaignCreateRequest } from '@/lib/api'

const form: CampaignCreateRequest = {
  name: 'Spring',
  geo: ['AU'],
  offer_id: 1,
  domain_id: 1,
  group_id: 1,
  traffic_source_id: 1,
}

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>
}

type CreateSpy = { mock: { calls: Parameters<typeof api.createCampaign>[] } }
const keys = (spy: CreateSpy) => spy.mock.calls.map(([, key]) => key)

describe('useCreateCampaign idempotency key', () => {
  afterEach(() => vi.restoreAllMocks())

  it('reuses the key when the same form is submitted again, and changes it for new values', async () => {
    const spy = vi
      .spyOn(api, 'createCampaign')
      .mockRejectedValue(new ApiError(503, { code: 'keitaro_unavailable', message: 'down' }))
    const { result } = renderHook(() => useCreateCampaign(), { wrapper })

    await act(() => result.current.mutateAsync(form).catch(() => undefined))
    await act(() => result.current.mutateAsync(form).catch(() => undefined))
    await act(() =>
      result.current.mutateAsync({ ...form, name: 'Autumn' }).catch(() => undefined),
    )

    const [first, retry, changed] = keys(spy)
    expect(retry).toBe(first)
    expect(changed).not.toBe(first)
  })

  it('starts a new key after a successful create', async () => {
    const spy = vi.spyOn(api, 'createCampaign').mockResolvedValue({ id: 1 } as CampaignCreated)
    const { result } = renderHook(() => useCreateCampaign(), { wrapper })

    await act(() => result.current.mutateAsync(form))
    await act(() => result.current.mutateAsync(form))

    const [first, second] = keys(spy)
    expect(second).not.toBe(first)
  })
})
