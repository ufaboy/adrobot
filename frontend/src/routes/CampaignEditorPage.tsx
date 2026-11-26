import { RefreshCwIcon } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router'

import { StreamCard } from '@/components/editor/StreamCard'
import { LoadError } from '@/components/LoadError'
import { SlowHint } from '@/components/SlowHint'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { useCampaignEditor, useFetchCampaign } from '@/hooks/use-campaign-editor'
import { useSingleFlight } from '@/hooks/use-single-flight'
import type { CampaignCreated } from '@/lib/api'

export function CampaignEditorPage() {
  const id = Number(useParams().id)
  const location = useLocation()
  const navigate = useNavigate()
  // The creator passes the new campaign in the navigation state. Keep it for this visit
  // only: history state survives a reload, so it is cleared once read.
  const [created] = useState(
    () => (location.state as { created?: CampaignCreated } | null)?.created,
  )
  useEffect(() => {
    if (location.state !== null) {
      void navigate(location.pathname, { replace: true, state: null })
    }
  }, [location.pathname, location.state, navigate])
  const campaign = useCampaignEditor(id)
  const fetchFromKeitaro = useFetchCampaign(id)
  const fetchOnce = useSingleFlight(fetchFromKeitaro)
  const [confirmOpen, setConfirmOpen] = useState(false)

  if (!Number.isInteger(id) || id <= 0) {
    return <p className="text-sm text-destructive">Invalid campaign id.</p>
  }

  const dirtyStreams = campaign.data?.streams.filter((s) => s.dirty) ?? []

  const fetchStreams = () => {
    setConfirmOpen(false)
    fetchOnce()
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link to="/" className="text-sm text-muted-foreground hover:underline">
            ← Campaigns
          </Link>
          <h1 className="text-xl font-semibold">
            {campaign.data?.name ?? `Campaign #${id}`}
          </h1>
          {campaign.data && (
            <p className="text-sm text-muted-foreground">
              Keitaro id {campaign.data.id} · alias {campaign.data.alias}
              {campaign.data.fetched_at &&
                ` · fetched ${new Date(campaign.data.fetched_at).toLocaleString()}`}
            </p>
          )}
        </div>
        <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row-reverse sm:items-center sm:gap-3">
          <Button
            variant="outline"
            className="w-full sm:w-auto"
            disabled={!campaign.data || fetchFromKeitaro.isPending}
            onClick={() => (dirtyStreams.length ? setConfirmOpen(true) : fetchStreams())}
          >
            <RefreshCwIcon className={fetchFromKeitaro.isPending ? 'animate-spin' : ''} />
            {fetchFromKeitaro.isPending ? 'Fetching…' : 'Fetch streams from KT'}
          </Button>
          <SlowHint pending={fetchFromKeitaro.isPending} />
        </div>
      </div>

      {created?.id === id && (
        <Alert>
          <AlertTitle>Campaign “{created.name}” created</AlertTitle>
          <AlertDescription>
            Geo {created.geo.join(', ')} → Google; everyone else → offer #{created.offer_id}.
          </AlertDescription>
        </Alert>
      )}

      {campaign.isError && (
        <LoadError
          title="Could not load the campaign"
          error={campaign.error}
          onRetry={() => void campaign.refetch()}
          retrying={campaign.isFetching}
        />
      )}

      {fetchFromKeitaro.isError && (
        <Alert variant="destructive">
          <AlertTitle>Fetch from Keitaro failed</AlertTitle>
          <AlertDescription>{fetchFromKeitaro.error.message}</AlertDescription>
        </Alert>
      )}

      {campaign.isPending && <p className="text-sm text-muted-foreground">Loading streams…</p>}

      {campaign.data?.streams.length === 0 && (
        <p className="text-sm text-muted-foreground">This campaign has no streams.</p>
      )}

      <div className="space-y-4">
        {campaign.data?.streams.map((stream) => (
          <StreamCard key={stream.id} campaignId={id} stream={stream} />
        ))}
      </div>

      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Discard unpublished changes?</DialogTitle>
            <DialogDescription>
              {dirtyStreams.map((s) => s.name).join(', ')}{' '}
              {dirtyStreams.length === 1 ? 'has' : 'have'} changes that were not pushed to
              Keitaro. Fetching replaces them with the current state from Keitaro.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmOpen(false)}>
              Keep editing
            </Button>
            <Button variant="destructive" onClick={fetchStreams}>
              Discard and fetch
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  )
}
