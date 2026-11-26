"""Draft / published rules for a stream's offers.

The functions mutate in-memory ORM objects only (no I/O), so they are unit-testable.
Rows removed from `stream.offers` are deleted by the delete-orphan cascade.
"""

from collections.abc import Sequence

from app.integrations.keitaro.schemas import KeitaroStreamOffer
from app.models import OfferState, Stream, StreamOffer
from app.services.weights import WeightInput, push_blocker, rebalance


def _inputs(offers: Sequence[StreamOffer]) -> list[WeightInput]:
    return [
        WeightInput(active=o.state == OfferState.ACTIVE, pinned=o.pinned, share=o.share)
        for o in offers
    ]


def ordered(stream: Stream) -> list[StreamOffer]:
    return sorted(stream.offers, key=lambda o: o.position)


def duplicate_offer_ids(remote: Sequence[KeitaroStreamOffer]) -> list[int]:
    """Offer ids a Keitaro stream lists more than once (the snapshot cannot hold them)."""
    seen: set[int] = set()
    duplicates: list[int] = []
    for item in remote:
        if item.offer_id in seen and item.offer_id not in duplicates:
            duplicates.append(item.offer_id)
        seen.add(item.offer_id)
    return duplicates


def apply_fetched_offers(stream: Stream, remote: Sequence[KeitaroStreamOffer]) -> None:
    """Make the snapshot match Keitaro, discarding unpublished changes.

    - Offers active in Keitaro become active with Keitaro's share (in Keitaro's order).
    - Offers known locally but missing in Keitaro, or not active there (e.g. disabled),
      become removed (archived, share 0); a removed offer is not sent on push.
    - Offers added locally and never pushed are dropped.
    - Published pins are preserved.
    """
    existing = {o.offer_id: o for o in stream.offers}
    for row in list(stream.offers):
        if row.is_new:
            stream.offers.remove(row)
            del existing[row.offer_id]

    active_remote = [item for item in remote if item.state == OfferState.ACTIVE]
    remote_ids: set[int] = set()
    for position, item in enumerate(active_remote):
        remote_ids.add(item.offer_id)
        found = existing.get(item.offer_id)
        if found is None:
            row = StreamOffer(offer_id=item.offer_id, published_pinned=False)
            stream.offers.append(row)
        else:
            row = found
        row.state = OfferState.ACTIVE
        row.share = item.share
        row.pinned = bool(row.published_pinned)
        row.position = position
        row.mark_published()

    for item in remote:
        if item.state != OfferState.ACTIVE and item.offer_id not in existing:
            row = StreamOffer(
                offer_id=item.offer_id, position=len(stream.offers), published_pinned=False
            )
            existing[item.offer_id] = row
            stream.offers.append(row)

    archived = [o for o in ordered(stream) if o.offer_id not in remote_ids]
    for offset, row in enumerate(archived, start=len(active_remote)):
        row.state = OfferState.REMOVED
        row.share = 0
        row.pinned = False
        row.position = offset
        row.mark_published()


def rebalance_stream(stream: Stream) -> None:
    """Recalculate shares after an edit. Raises `WeightError` if pins exceed 100%."""
    offers = ordered(stream)
    for offer, share in zip(offers, rebalance(_inputs(offers)), strict=True):
        if offer.state != OfferState.ACTIVE:
            offer.pinned = False
        offer.share = share


def stream_push_blocker(stream: Stream) -> str | None:
    return push_blocker(_inputs(stream.offers))


def payload_offers(stream: Stream) -> list[KeitaroStreamOffer]:
    """The offer list sent to Keitaro on push: active offers only."""
    return [
        KeitaroStreamOffer(offer_id=o.offer_id, share=o.share, state="active")
        for o in ordered(stream)
        if o.state == OfferState.ACTIVE
    ]


type OfferShares = dict[int, int]


def remote_shares(remote: Sequence[KeitaroStreamOffer]) -> OfferShares:
    """Active offers of a Keitaro stream as {offer_id: share}."""
    return {o.offer_id: o.share for o in remote if o.state == OfferState.ACTIVE}


def published_shares(stream: Stream) -> OfferShares:
    """The active offers last synced with Keitaro."""
    return {
        o.offer_id: o.published_share or 0
        for o in stream.offers
        if o.published_state == OfferState.ACTIVE
    }


def draft_shares(stream: Stream) -> OfferShares:
    """The active offers a push would send."""
    return {o.offer_id: o.share for o in payload_offers(stream)}


def mark_pushed(stream: Stream) -> None:
    """Record the current draft as published.

    Offers added and removed before publishing never reached Keitaro, so they are dropped.
    """
    for row in list(stream.offers):
        if row.is_new and row.state == OfferState.REMOVED:
            stream.offers.remove(row)
        else:
            row.mark_published()


def cancel_changes(stream: Stream) -> None:
    """Revert every unpublished change to the last state synced with Keitaro."""
    for row in list(stream.offers):
        if row.is_new:
            stream.offers.remove(row)
            continue
        assert row.published_state is not None
        assert row.published_share is not None
        row.state = row.published_state
        row.share = row.published_share
        row.pinned = bool(row.published_pinned)
