import { RefreshCwIcon } from 'lucide-react'
import { useState } from 'react'
import { Link, useLocation, useParams } from 'react-router'

import { StreamCard } from '@/components/editor/StreamCard'
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
import type { CampaignCreated } from '@/lib/api'

export function CampaignEditorPage() {
  const id = Number(useParams().id)
  const created = (useLocation().state as { created?: CampaignCreated } | null)?.created
  const campaign = useCampaignEditor(id)
  const fetchFromKeitaro = useFetchCampaign(id)
  const [confirmOpen, setConfirmOpen] = useState(false)

  if (!Number.isInteger(id) || id <= 0) {
    return <p className="text-sm text-destructive">Invalid campaign id.</p>
  }

  const dirtyStreams = campaign.data?.streams.filter((s) => s.dirty) ?? []

  const fetchStreams = () => {
    setConfirmOpen(false)
    fetchFromKeitaro.mutate()
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
        <Button
          variant="outline"
          disabled={!campaign.data || fetchFromKeitaro.isPending}
          onClick={() => (dirtyStreams.length ? setConfirmOpen(true) : fetchStreams())}
        >
          <RefreshCwIcon className={fetchFromKeitaro.isPending ? 'animate-spin' : ''} />
          Fetch streams from KT
        </Button>
      </div>

      {created && (
        <Alert>
          <AlertTitle>Campaign “{created.name}” created</AlertTitle>
          <AlertDescription>
            Geo {created.geo.join(', ')} → Google; everyone else → offer #{created.offer_id}.
          </AlertDescription>
        </Alert>
      )}

      {(campaign.error ?? fetchFromKeitaro.error) && (
        <Alert variant="destructive">
          <AlertTitle>Keitaro request failed</AlertTitle>
          <AlertDescription>
            {(campaign.error ?? fetchFromKeitaro.error)?.message}
          </AlertDescription>
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
