import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

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

export function useCreateCampaign() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: CampaignCreateRequest) => api.createCampaign(data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['campaigns'] }),
  })
}
