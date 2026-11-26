import { PinIcon, PinOffIcon, Trash2Icon, Undo2Icon, UploadIcon, XIcon } from 'lucide-react'
import { useState } from 'react'

import { AddOfferAction } from '@/components/editor/AddOfferAction'
import { ShareInput } from '@/components/editor/ShareInput'
import { OfferCombobox } from '@/components/OfferCombobox'
import { SlowHint } from '@/components/SlowHint'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { type StreamAction, useStreamAction } from '@/hooks/use-campaign-editor'
import { useSingleFlight } from '@/hooks/use-single-flight'
import type { Offer, Stream } from '@/lib/api'
import { cn } from '@/lib/utils'

interface StreamCardProps {
  campaignId: number
  stream: Stream
}

// Mobile first: an offer is a small card (name on top, controls below);
// from md up the rows line up as a four-column table.
const ROW_GRID =
  'grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-x-3 gap-y-2 md:grid-cols-[minmax(0,1fr)_8rem_6rem_8rem]'

export function StreamCard({ campaignId, stream }: StreamCardProps) {
  const action = useStreamAction(campaignId, stream.id)
  const [picked, setPicked] = useState<Offer | null>(null)
  const busy = action.isPending

  // One action at a time: a double click must not send the same change twice.
  const run = useSingleFlight(action)

  /** Whether `type` (for `offerId`, if given) is the action currently running. */
  const running = (type: StreamAction['type'], offerId?: number): boolean => {
    const current = busy ? action.variables : undefined
    if (current?.type !== type) return false
    return offerId === undefined || ('offerId' in current && current.offerId === offerId)
  }

  return (
    <section
      aria-label={`Stream ${stream.name}`}
      data-dirty={stream.dirty || undefined}
      className={cn(
        'rounded-xl border bg-card p-3 shadow-xs transition-colors sm:p-4',
        stream.dirty && 'border-amber-300 bg-amber-50',
      )}
    >
      <header className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="font-medium">
            <span className="text-muted-foreground">#{stream.position}</span> {stream.name}
          </h2>
          <Badge variant="outline">{stream.type}</Badge>
          <span className="font-mono text-xs text-muted-foreground">id {stream.id}</span>
          {stream.dirty && (
            <Badge className="bg-amber-200 text-amber-900 hover:bg-amber-200">Unpublished</Badge>
          )}
        </div>

        {stream.editable && (
          <div className="flex gap-2 sm:ml-auto">
            <Button
              variant="outline"
              className="flex-1 sm:flex-none"
              disabled={!stream.dirty || busy}
              loading={running('cancel')}
              onClick={() => run({ type: 'cancel' })}
            >
              <XIcon />
              Cancel
            </Button>
            <Button
              className="flex-1 sm:flex-none"
              disabled={!stream.dirty || stream.push_blocker !== null || busy}
              loading={running('push')}
              title={stream.push_blocker ?? undefined}
              onClick={() => run({ type: 'push' })}
            >
              <UploadIcon />
              {running('push') ? 'Pushing…' : 'Push to Keitaro'}
            </Button>
          </div>
        )}
      </header>

      <div className="mt-2 empty:hidden">
        <SlowHint pending={busy} />
      </div>

      {!stream.editable ? (
        <p className="mt-3 text-sm text-muted-foreground">
          No offers in this stream. Its filters and actions are managed in Keitaro.
        </p>
      ) : (
        <div className="mt-3 space-y-3">
          <div role="table" aria-label="Offers" className="text-sm">
            <div role="rowgroup" className="hidden md:block">
              <div
                role="row"
                className={cn(ROW_GRID, 'border-b px-2 py-2 font-medium text-muted-foreground')}
              >
                <span role="columnheader">Offer</span>
                <span role="columnheader">Share</span>
                <span role="columnheader">State</span>
                <span role="columnheader" className="text-right">
                  Actions
                </span>
              </div>
            </div>

            <div role="rowgroup" className="divide-y">
              {stream.offers.map((offer) => {
                const removed = offer.state === 'removed'
                // Fade the removed offer's data, but not its "Bring back" action.
                const faded = removed && 'text-muted-foreground opacity-60'
                const shareRunning =
                  running('setShare', offer.offer_id) || running('unpin', offer.offer_id)
                return (
                  <div
                    role="row"
                    key={offer.offer_id}
                    data-state={removed ? 'removed' : 'active'}
                    className={cn(ROW_GRID, 'py-3 md:px-2 md:py-2')}
                  >
                    <div
                      role="cell"
                      className={cn('col-span-3 flex min-w-0 gap-2 md:col-span-1', faded)}
                    >
                      <span className="pt-0.5 font-mono text-xs text-muted-foreground">
                        {offer.offer_id}
                      </span>
                      <span className={cn('min-w-0 break-words md:truncate', removed && 'line-through')}>
                        {offer.name ?? `Offer #${offer.offer_id}`}
                      </span>
                    </div>

                    <div role="cell" className={cn('flex items-center gap-1', faded)}>
                      <ShareInput
                        offerId={offer.offer_id}
                        value={offer.share}
                        disabled={removed || busy}
                        onCommit={(share, revert) =>
                          // A rejected share (e.g. pins above 100%) must not stay in the field.
                          run(
                            { type: 'setShare', offerId: offer.offer_id, share },
                            { onError: revert },
                          )
                        }
                      />
                      {!removed && (
                        <Button
                          size="icon-sm"
                          variant={offer.pinned ? 'secondary' : 'ghost'}
                          aria-pressed={offer.pinned}
                          aria-label={offer.pinned ? 'Unpin share' : 'Pin share'}
                          title={
                            offer.pinned
                              ? 'Pinned: kept on recalculation. Click to unpin.'
                              : 'Pin the current share'
                          }
                          disabled={busy}
                          loading={shareRunning}
                          onClick={() =>
                            run(
                              offer.pinned
                                ? { type: 'unpin', offerId: offer.offer_id }
                                : { type: 'setShare', offerId: offer.offer_id, share: offer.share },
                            )
                          }
                        >
                          {offer.pinned ? <PinIcon /> : <PinOffIcon className="opacity-40" />}
                        </Button>
                      )}
                    </div>

                    <div role="cell" className={cn(faded)}>
                      {removed ? (
                        <Badge variant="outline">removed</Badge>
                      ) : offer.is_new ? (
                        <Badge className="bg-amber-200 text-amber-900">new</Badge>
                      ) : (
                        <Badge variant="secondary">active</Badge>
                      )}
                    </div>

                    <div role="cell" className="justify-self-end">
                      {removed ? (
                        <Button
                          size="sm"
                          variant="secondary"
                          disabled={busy}
                          loading={running('bringBack', offer.offer_id)}
                          onClick={() => run({ type: 'bringBack', offerId: offer.offer_id })}
                        >
                          <Undo2Icon />
                          Bring back
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          variant="ghost"
                          disabled={busy}
                          loading={running('remove', offer.offer_id)}
                          onClick={() => run({ type: 'remove', offerId: offer.offer_id })}
                        >
                          <Trash2Icon />
                          Remove
                        </Button>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2 border-t pt-3 text-sm">
            <span className={cn(stream.total_share !== 100 && 'font-medium text-destructive')}>
              Total: {stream.total_share}%
            </span>
            {stream.dirty && stream.push_blocker && (
              <span role="status" className="text-destructive">
                {stream.push_blocker}
              </span>
            )}
          </div>

          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <div className="min-w-0 flex-1">
              <OfferCombobox value={picked} onChange={setPicked} />
            </div>
            <AddOfferAction
              offer={picked}
              streamOffers={stream.offers}
              disabled={busy}
              loading={picked !== null && (running('add', picked.id) || running('bringBack', picked.id))}
              className="w-full sm:w-auto"
              onAdd={(offerId) =>
                run({ type: 'add', offerId }, { onSuccess: () => setPicked(null) })
              }
              onBringBack={(offerId) =>
                run({ type: 'bringBack', offerId }, { onSuccess: () => setPicked(null) })
              }
            />
          </div>

          {action.error && (
            <Alert variant="destructive">
              <AlertDescription>{action.error.message}</AlertDescription>
            </Alert>
          )}
        </div>
      )}
    </section>
  )
}
