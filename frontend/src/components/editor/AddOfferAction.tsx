import { PlusIcon, Undo2Icon } from 'lucide-react'

import { Button } from '@/components/ui/button'
import type { Offer, StreamOffer } from '@/lib/api'

interface AddOfferActionProps {
  offer: Offer | null
  streamOffers: StreamOffer[]
  disabled?: boolean
  /** The add / bring-back request for the picked offer is running. */
  loading?: boolean
  className?: string
  onAdd: (offerId: number) => void
  onBringBack: (offerId: number) => void
}

/**
 * The action for the offer picked in the "add offer" picker:
 * an offer already in the stream as removed is brought back instead of added again.
 */
export function AddOfferAction({
  offer,
  streamOffers,
  disabled,
  loading,
  className,
  onAdd,
  onBringBack,
}: AddOfferActionProps) {
  const existing = offer ? streamOffers.find((o) => o.offer_id === offer.id) : undefined

  if (offer && existing?.state === 'removed') {
    return (
      <Button
        variant="secondary"
        className={className}
        disabled={disabled}
        loading={loading}
        onClick={() => onBringBack(offer.id)}
      >
        <Undo2Icon />
        Bring back
      </Button>
    )
  }

  if (existing?.state === 'active') {
    return (
      <Button variant="outline" className={className} disabled>
        Already in stream
      </Button>
    )
  }

  return (
    <Button
      className={className}
      disabled={disabled || !offer}
      loading={loading}
      onClick={() => offer && onAdd(offer.id)}
    >
      <PlusIcon />
      Add offer
    </Button>
  )
}
