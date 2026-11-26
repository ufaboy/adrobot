"""Unit tests for fetch / edit / push / cancel rules on in-memory stream snapshots."""

from app.integrations.keitaro.schemas import KeitaroStreamOffer
from app.models import OfferState, Stream, StreamOffer
from app.services import stream_rules


def published(offer_id: int, share: int, *, pinned: bool = False, position: int = 0) -> StreamOffer:
    row = StreamOffer(
        offer_id=offer_id, state=OfferState.ACTIVE, share=share, pinned=pinned, position=position
    )
    row.mark_published()
    return row


def make_stream(*offers: StreamOffer) -> Stream:
    return Stream(keitaro_id=1, name="Offers", type="regular", position=2, offers=list(offers))


def kt(offer_id: int, share: int) -> KeitaroStreamOffer:
    return KeitaroStreamOffer(offer_id=offer_id, share=share, state="active")


def snapshot(stream: Stream) -> list[tuple[int, str, int, bool]]:
    return [(o.offer_id, o.state, o.share, o.pinned) for o in stream_rules.ordered(stream)]


# --- Fetch ---------------------------------------------------------------------------


def test_fetch_into_empty_stream_takes_keitaro_offers_as_published() -> None:
    stream = make_stream()

    stream_rules.apply_fetched_offers(stream, [kt(1, 34), kt(2, 33), kt(3, 33)])

    assert snapshot(stream) == [
        (1, "active", 34, False),
        (2, "active", 33, False),
        (3, "active", 33, False),
    ]
    assert not stream.is_dirty


def test_fetch_marks_offers_missing_in_keitaro_as_removed() -> None:
    stream = make_stream(published(1, 50), published(2, 50, position=1))

    stream_rules.apply_fetched_offers(stream, [kt(2, 100)])

    assert snapshot(stream) == [(2, "active", 100, False), (1, "removed", 0, False)]
    assert not stream.is_dirty


def test_fetch_adds_offers_new_in_keitaro_and_takes_their_shares() -> None:
    stream = make_stream(published(1, 100))

    stream_rules.apply_fetched_offers(stream, [kt(1, 70), kt(9, 30)])

    assert snapshot(stream) == [(1, "active", 70, False), (9, "active", 30, False)]


def test_fetch_preserves_published_pins() -> None:
    stream = make_stream(published(1, 25, pinned=True), published(2, 75, position=1))

    stream_rules.apply_fetched_offers(stream, [kt(1, 25), kt(2, 75)])

    assert snapshot(stream) == [(1, "active", 25, True), (2, "active", 75, False)]


def test_fetch_discards_unpublished_changes() -> None:
    stream = make_stream(published(1, 50), published(2, 50, position=1))
    stream.offers[0].pinned = True  # unpublished pin
    stream.offers[1].state = OfferState.REMOVED  # unpublished removal
    stream.offers.append(
        StreamOffer(offer_id=3, state=OfferState.ACTIVE, share=34, pinned=False, position=2)
    )

    stream_rules.apply_fetched_offers(stream, [kt(1, 50), kt(2, 50)])

    assert snapshot(stream) == [(1, "active", 50, False), (2, "active", 50, False)]
    assert not stream.is_dirty


def test_offer_removed_in_keitaro_can_be_brought_back_after_fetch() -> None:
    stream = make_stream(published(1, 50), published(2, 50, position=1))
    stream_rules.apply_fetched_offers(stream, [kt(1, 100)])

    removed = next(o for o in stream.offers if o.offer_id == 2)
    removed.state = OfferState.ACTIVE
    stream_rules.rebalance_stream(stream)

    assert snapshot(stream) == [(1, "active", 50, False), (2, "active", 50, False)]
    assert stream.is_dirty


# --- Edits, push and cancel --------------------------------------------------------


def test_adding_an_offer_rebalances_and_marks_stream_dirty() -> None:
    stream = make_stream(
        published(1, 34), published(2, 33, position=1), published(3, 33, position=2)
    )
    stream.offers.append(
        StreamOffer(offer_id=4, state=OfferState.ACTIVE, share=0, pinned=False, position=3)
    )

    stream_rules.rebalance_stream(stream)

    assert [o.share for o in stream_rules.ordered(stream)] == [25, 25, 25, 25]
    assert stream.is_dirty


def test_removing_a_pinned_offer_unpins_it() -> None:
    stream = make_stream(published(1, 25, pinned=True), published(2, 75, position=1))
    stream.offers[0].state = OfferState.REMOVED

    stream_rules.rebalance_stream(stream)

    assert snapshot(stream) == [(1, "removed", 0, False), (2, "active", 100, False)]


def test_payload_contains_only_active_offers_in_order() -> None:
    stream = make_stream(
        published(1, 50), published(2, 0, position=1), published(3, 50, position=2)
    )
    stream.offers[1].state = OfferState.REMOVED

    payload = stream_rules.payload_offers(stream)

    assert [(o.offer_id, o.share) for o in payload] == [(1, 50), (3, 50)]


def test_mark_pushed_makes_draft_published_and_drops_never_published_removals() -> None:
    stream = make_stream(published(1, 100))
    stream.offers.append(
        StreamOffer(offer_id=2, state=OfferState.REMOVED, share=0, pinned=False, position=1)
    )
    stream.offers[0].share = 100

    stream_rules.mark_pushed(stream)

    assert snapshot(stream) == [(1, "active", 100, False)]
    assert not stream.is_dirty


def test_cancel_reverts_all_changes_and_drops_added_offers() -> None:
    stream = make_stream(published(1, 50), published(2, 50, position=1))
    stream.offers[0].state = OfferState.REMOVED
    stream.offers[1].pinned = True
    stream.offers.append(
        StreamOffer(offer_id=3, state=OfferState.ACTIVE, share=34, pinned=False, position=2)
    )
    stream_rules.rebalance_stream(stream)
    assert stream.is_dirty

    stream_rules.cancel_changes(stream)

    assert snapshot(stream) == [(1, "active", 50, False), (2, "active", 50, False)]
    assert not stream.is_dirty


def test_push_blocker_reports_when_all_pinned_shares_do_not_sum_to_100() -> None:
    stream = make_stream(published(1, 50), published(2, 50, position=1))
    stream.offers[0].share, stream.offers[0].pinned = 30, True
    stream.offers[1].share, stream.offers[1].pinned = 30, True
    stream_rules.rebalance_stream(stream)

    assert stream_rules.stream_push_blocker(stream) == (
        "Shares add up to 60%, not 100%. Adjust or unpin a share."
    )
