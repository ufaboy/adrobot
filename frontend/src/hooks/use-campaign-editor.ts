import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api, type CampaignEditor, type Stream } from '@/lib/api'

export const campaignKey = (id: number) => ['campaigns', id] as const

/** Campaigns from Keitaro; cached for a minute, the list page has a Refresh button. */
export function useCampaigns() {
  return useQuery({
    queryKey: ['campaigns', 'list'],
    queryFn: api.listCampaigns,
    staleTime: 60 * 1000,
  })
}

export function useCampaignEditor(id: number) {
  return useQuery({ queryKey: campaignKey(id), queryFn: () => api.getCampaign(id) })
}

/** Re-read streams from Keitaro; replaces the cached snapshot. */
export function useFetchCampaign(id: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => api.fetchCampaign(id),
    onSuccess: (campaign) => queryClient.setQueryData(campaignKey(id), campaign),
  })
}

export type StreamAction =
  | { type: 'add'; offerId: number }
  | { type: 'remove'; offerId: number }
  | { type: 'bringBack'; offerId: number }
  | { type: 'setShare'; offerId: number; share: number }
  | { type: 'unpin'; offerId: number }
  | { type: 'push' }
  | { type: 'cancel' }

function runAction(streamId: number, action: StreamAction): Promise<Stream> {
  switch (action.type) {
    case 'add':
      return api.addOffer(streamId, action.offerId)
    case 'remove':
      return api.removeOffer(streamId, action.offerId)
    case 'bringBack':
      return api.bringBackOffer(streamId, action.offerId)
    case 'setShare':
      return api.setShare(streamId, action.offerId, action.share)
    case 'unpin':
      return api.unpin(streamId, action.offerId)
    case 'push':
      return api.pushStream(streamId)
    case 'cancel':
      return api.cancelStream(streamId)
  }
}

/** Every stream edit returns the recalculated stream, which replaces it in the cache. */
export function useStreamAction(campaignId: number, streamId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (action: StreamAction) => runAction(streamId, action),
    onSuccess: (stream) =>
      queryClient.setQueryData<CampaignEditor>(campaignKey(campaignId), (campaign) =>
        campaign
          ? { ...campaign, streams: campaign.streams.map((s) => (s.id === stream.id ? stream : s)) }
          : campaign,
      ),
  })
}
