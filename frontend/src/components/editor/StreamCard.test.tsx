import { fireEvent, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { AddOfferAction } from '@/components/editor/AddOfferAction'
import { StreamCard } from '@/components/editor/StreamCard'
import { api, type Offer, type Stream, type StreamOffer } from '@/lib/api'
import { renderWithProviders } from '@/test/render'

function streamOffer(overrides: Partial<StreamOffer> & { offer_id: number }): StreamOffer {
  return {
    name: `Offer ${overrides.offer_id}`,
    state: 'active',
    share: 50,
    pinned: false,
    is_new: false,
    is_dirty: false,
    published_share: 50,
    ...overrides,
  }
}

function makeStream(overrides: Partial<Stream> = {}): Stream {
  return {
    id: 653,
    name: 'Offers',
    type: 'regular',
    position: 2,
    editable: true,
    dirty: false,
    total_share: 100,
    push_blocker: null,
    offers: [streamOffer({ offer_id: 1 }), streamOffer({ offer_id: 2 })],
    ...overrides,
  }
}

const offer = (id: number): Offer => ({ id, name: `Offer ${id}`, state: 'active', countries: [] })

describe('StreamCard', () => {
  it('highlights a stream with unpublished changes and enables Push and Cancel', () => {
    renderWithProviders(
      <StreamCard
        campaignId={1}
        stream={makeStream({
          dirty: true,
          offers: [
            streamOffer({ offer_id: 1, share: 34 }),
            streamOffer({ offer_id: 2, state: 'removed', share: 0, is_dirty: true }),
            streamOffer({ offer_id: 3, share: 33, is_new: true, is_dirty: true }),
          ],
        })}
      />,
    )

    const card = screen.getByRole('region', { name: 'Stream Offers' })
    expect(card).toHaveAttribute('data-dirty', 'true')
    expect(within(card).getByText('Unpublished')).toBeInTheDocument()
    expect(within(card).getByRole('button', { name: /Push to Keitaro/ })).toBeEnabled()
    expect(within(card).getByRole('button', { name: /Cancel/ })).toBeEnabled()
    // A removed offer is greyed out and offers Bring back instead of Remove.
    const removedRow = within(card).getByText('Offer 2').closest('[role="row"]')
    expect(removedRow).toHaveAttribute('data-state', 'removed')
    const bringBack = within(removedRow as HTMLElement).getByRole('button', { name: /Bring back/ })
    expect(bringBack).toBeVisible()
    // The offer's data is faded, its action is not (it must not look disabled).
    expect(within(removedRow as HTMLElement).getByText('Offer 2').closest('.opacity-60')).not.toBeNull()
    expect(bringBack.closest('.opacity-60')).toBeNull()
  })

  it('blocks Push and shows the reason when shares do not add up to 100', () => {
    renderWithProviders(
      <StreamCard
        campaignId={1}
        stream={makeStream({
          dirty: true,
          total_share: 60,
          push_blocker: 'Shares add up to 60%, not 100%. Adjust or unpin a share.',
          offers: [
            streamOffer({ offer_id: 1, share: 30, pinned: true, is_dirty: true }),
            streamOffer({ offer_id: 2, share: 30, pinned: true, is_dirty: true }),
          ],
        })}
      />,
    )

    expect(screen.getByRole('button', { name: /Push to Keitaro/ })).toBeDisabled()
    expect(screen.getByRole('status')).toHaveTextContent('Shares add up to 60%')
    expect(screen.getByText('Total: 60%')).toBeInTheDocument()
  })

  it('shows a read-only note for streams without offers', () => {
    renderWithProviders(
      <StreamCard campaignId={1} stream={makeStream({ editable: false, offers: [] })} />,
    )

    expect(screen.getByText(/No offers in this stream/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Push to Keitaro/ })).not.toBeInTheDocument()
  })
})

describe('AddOfferAction', () => {
  const streamOffers = [
    streamOffer({ offer_id: 1 }),
    streamOffer({ offer_id: 2, state: 'removed', share: 0 }),
  ]

  it('offers Bring back instead of Add for an offer removed from the stream', async () => {
    const onAdd = vi.fn()
    const onBringBack = vi.fn()
    renderWithProviders(
      <AddOfferAction
        offer={offer(2)}
        streamOffers={streamOffers}
        onAdd={onAdd}
        onBringBack={onBringBack}
      />,
    )

    await userEvent.click(screen.getByRole('button', { name: /Bring back/ }))

    expect(onBringBack).toHaveBeenCalledWith(2)
    expect(onAdd).not.toHaveBeenCalled()
  })

  it('does not allow adding an offer that is already active', () => {
    renderWithProviders(
      <AddOfferAction
        offer={offer(1)}
        streamOffers={streamOffers}
        onAdd={vi.fn()}
        onBringBack={vi.fn()}
      />,
    )

    expect(screen.getByRole('button', { name: 'Already in stream' })).toBeDisabled()
  })

  it('adds a new offer', async () => {
    const onAdd = vi.fn()
    renderWithProviders(
      <AddOfferAction offer={offer(9)} streamOffers={streamOffers} onAdd={onAdd} onBringBack={vi.fn()} />,
    )

    await userEvent.click(screen.getByRole('button', { name: /Add offer/ }))

    expect(onAdd).toHaveBeenCalledWith(9)
  })
})

describe('StreamCard double clicks', () => {
  afterEach(() => vi.restoreAllMocks())

  it('sends one request when Remove is double-clicked', async () => {
    let finish: (stream: Stream) => void = () => undefined
    const remove = vi
      .spyOn(api, 'removeOffer')
      .mockImplementation(() => new Promise<Stream>((resolve) => (finish = resolve)))
    renderWithProviders(<StreamCard campaignId={1} stream={makeStream()} />)

    const [removeFirst] = screen.getAllByRole('button', { name: /Remove/ })
    // Two clicks in the same task, as a real double click arrives: React has not
    // re-rendered the button as disabled in between.
    fireEvent.click(removeFirst)
    fireEvent.click(removeFirst)
    await vi.waitFor(() => expect(remove).toHaveBeenCalled())
    await new Promise((resolve) => setTimeout(resolve, 50))
    expect(remove).toHaveBeenCalledOnce()

    // Once the first request settles, the next click goes through again.
    finish(makeStream())
    await vi.waitFor(() => expect(removeFirst).toBeEnabled())
    await userEvent.click(removeFirst)
    expect(remove).toHaveBeenCalledTimes(2)
  })
})
