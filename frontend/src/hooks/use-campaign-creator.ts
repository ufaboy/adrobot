import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useRef } from 'react'

import { useDebouncedValue } from '@/hooks/use-debounced-value'
import { api, type CampaignCreateRequest } from '@/lib/api'

export function useReference() {
  return useQuery({
    queryKey: ['reference'],
    queryFn: api.reference,
    staleTime: 10 * 60 * 1000,
  })
}

/**
 * Debounced offer search. `settled` is true once the shown results belong to the
 * current query: no pending debounce, no request in flight, no placeholder data.
 */
export function useOfferSearch(query: string, enabled: boolean) {
  const term = query.trim()
  const debounced = useDebouncedValue(term, 250)
  const result = useQuery({
    queryKey: ['offers', 'search', debounced],
    queryFn: () => api.searchOffers(debounced),
    enabled,
    staleTime: 60 * 1000,
    placeholderData: keepPreviousData,
  })
  const settled = debounced === term && !result.isFetching && !result.isPlaceholderData
  return { result, settled }
}

export function useRefreshOffers() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: api.refreshOffers,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['offers'] }),
  })
}

/**
 * Create a campaign with an idempotency key per filled-in form: re-submitting the same
 * values (a double click, a retry after a lost response) reuses the key, so the backend
 * returns the first result instead of creating a second campaign. Changing any value
 * starts a new key, as does a successful create.
 */
export function useCreateCampaign() {
  const queryClient = useQueryClient()
  const attempt = useRef<{ body: string; key: string } | null>(null)

  return useMutation({
    mutationFn: (data: CampaignCreateRequest) => {
      const body = JSON.stringify(data)
      if (attempt.current?.body !== body) {
        attempt.current = { body, key: newIdempotencyKey() }
      }
      return api.createCampaign(data, attempt.current.key)
    },
    onSuccess: () => {
      attempt.current = null
      return queryClient.invalidateQueries({ queryKey: ['campaigns'] })
    },
  })
}

function newIdempotencyKey(): string {
  // randomUUID needs a secure context (https or localhost); fall back for plain http.
  if (typeof crypto.randomUUID === 'function') return crypto.randomUUID()
  return Array.from(crypto.getRandomValues(new Uint8Array(16)), (b) =>
    b.toString(16).padStart(2, '0'),
  ).join('')
}
