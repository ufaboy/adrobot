import { PinIcon, PinOffIcon, Trash2Icon, Undo2Icon, UploadIcon, XIcon } from 'lucide-react'
import { useState } from 'react'

import { AddOfferAction } from '@/components/editor/AddOfferAction'
import { ShareInput } from '@/components/editor/ShareInput'
import { OfferCombobox } from '@/components/OfferCombobox'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useStreamAction } from '@/hooks/use-campaign-editor'
import type { Offer, Stream } from '@/lib/api'
import { cn } from '@/lib/utils'

interface StreamCardProps {
  campaignId: number
  stream: Stream
}

export function StreamCard({ campaignId, stream }: StreamCardProps) {
  const action = useStreamAction(campaignId, stream.id)
  const [picked, setPicked] = useState<Offer | null>(null)
  const busy = action.isPending

  const run = (...args: Parameters<typeof action.mutate>) => {
    action.reset()
    action.mutate(...args)
  }

  return (
    <section
      aria-label={`Stream ${stream.name}`}
      data-dirty={stream.dirty || undefined}
      className={cn(
        'rounded-xl border bg-card p-4 shadow-xs transition-colors',
        stream.dirty && 'border-amber-300 bg-amber-50',
      )}
    >
      <header className="flex flex-wrap items-center gap-2">
        <h2 className="font-medium">
          <span className="text-muted-foreground">#{stream.position}</span> {stream.name}
        </h2>
        <Badge variant="outline">{stream.type}</Badge>
        <span className="font-mono text-xs text-muted-foreground">id {stream.id}</span>
        {stream.dirty && (
          <Badge className="bg-amber-200 text-amber-900 hover:bg-amber-200">Unpublished</Badge>
        )}

        {stream.editable && (
          <div className="ml-auto flex gap-2">
            <Button
              size="sm"
              variant="outline"
              disabled={!stream.dirty || busy}
              onClick={() => run({ type: 'cancel' })}
            >
              <XIcon />
              Cancel
            </Button>
            <Button
              size="sm"
              disabled={!stream.dirty || stream.push_blocker !== null || busy}
              title={stream.push_blocker ?? undefined}
              onClick={() => run({ type: 'push' })}
            >
              <UploadIcon />
              Push to Keitaro
            </Button>
          </div>
        )}
      </header>

      {!stream.editable ? (
        <p className="mt-3 text-sm text-muted-foreground">
          No offers in this stream. Its filters and actions are managed in Keitaro.
        </p>
      ) : (
        <div className="mt-3 space-y-3">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Offer</TableHead>
                <TableHead className="w-32">Share</TableHead>
                <TableHead className="w-24">State</TableHead>
                <TableHead className="w-40 text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {stream.offers.map((offer) => {
                const removed = offer.state === 'removed'
                return (
                  <TableRow
                    key={offer.offer_id}
                    data-state={removed ? 'removed' : 'active'}
                    className={cn(removed && 'text-muted-foreground opacity-60')}
                  >
                    <TableCell className="max-w-md">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs text-muted-foreground">
                          {offer.offer_id}
                        </span>
                        <span className={cn('truncate', removed && 'line-through')}>
                          {offer.name ?? `Offer #${offer.offer_id}`}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <ShareInput
                          offerId={offer.offer_id}
                          value={offer.share}
                          disabled={removed || busy}
                          onCommit={(share) =>
                            run({ type: 'setShare', offerId: offer.offer_id, share })
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
                    </TableCell>
                    <TableCell>
                      {removed ? (
                        <Badge variant="outline">removed</Badge>
                      ) : offer.is_new ? (
                        <Badge className="bg-amber-200 text-amber-900">new</Badge>
                      ) : (
                        <Badge variant="secondary">active</Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      {removed ? (
                        <Button
                          size="sm"
                          variant="secondary"
                          disabled={busy}
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
                          onClick={() => run({ type: 'remove', offerId: offer.offer_id })}
                        >
                          <Trash2Icon />
                          Remove
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>

          <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
            <span className={cn(stream.total_share !== 100 && 'font-medium text-destructive')}>
              Total: {stream.total_share}%
            </span>
            {stream.dirty && stream.push_blocker && (
              <span role="status" className="text-destructive">
                {stream.push_blocker}
              </span>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="min-w-64 flex-1">
              <OfferCombobox value={picked} onChange={setPicked} />
            </div>
            <AddOfferAction
              offer={picked}
              streamOffers={stream.offers}
              disabled={busy}
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
