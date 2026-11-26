import pytest

from app.services.weights import WeightError, WeightInput, push_blocker, rebalance


def active(share: int = 0, *, pinned: bool = False) -> WeightInput:
    return WeightInput(active=True, pinned=pinned, share=share)


def removed() -> WeightInput:
    return WeightInput(active=False, pinned=False, share=0)


@pytest.mark.parametrize(
    ("count", "expected"),
    [
        (1, [100]),
        (2, [50, 50]),
        (3, [34, 33, 33]),
        (4, [25, 25, 25, 25]),
        (6, [17, 17, 17, 17, 16, 16]),
        (7, [15, 15, 14, 14, 14, 14, 14]),
    ],
)
def test_splits_evenly_with_largest_remainder(count: int, expected: list[int]) -> None:
    shares = rebalance([active() for _ in range(count)])

    assert shares == expected
    assert sum(shares) == 100


def test_pinned_share_is_kept_and_rest_is_split() -> None:
    # The video scenario: one offer pinned at 25%, two others share the remaining 75%.
    shares = rebalance([active(25, pinned=True), active(), active()])

    assert shares == [25, 38, 37]


def test_removed_offers_get_zero_and_are_ignored() -> None:
    shares = rebalance([active(), removed(), active(), removed()])

    assert shares == [50, 0, 50, 0]


def test_leftover_units_follow_position_not_pinned_offers() -> None:
    shares = rebalance([active(10, pinned=True), active(), active(), active()])

    assert shares == [10, 30, 30, 30]


def test_remainder_with_odd_split_after_pin() -> None:
    shares = rebalance([active(), active(1, pinned=True), active(), active()])

    assert shares == [33, 1, 33, 33]


def test_pins_summing_to_100_leave_zero_for_unpinned() -> None:
    shares = rebalance([active(60, pinned=True), active(40, pinned=True), active()])

    assert shares == [60, 40, 0]


def test_all_pinned_below_100_keeps_values() -> None:
    shares = rebalance([active(30, pinned=True), active(30, pinned=True)])

    assert shares == [30, 30]


def test_pins_over_100_are_rejected() -> None:
    with pytest.raises(WeightError, match="110%"):
        rebalance([active(60, pinned=True), active(50, pinned=True), active()])


def test_pinned_flag_on_removed_offer_is_ignored() -> None:
    offers = [WeightInput(active=False, pinned=True, share=80), active(), active()]

    assert rebalance(offers) == [0, 50, 50]


def test_empty_stream() -> None:
    assert rebalance([]) == []


def test_push_allowed_when_active_shares_sum_to_100() -> None:
    assert push_blocker([active(34), active(33), active(33), removed()]) is None


def test_push_blocked_when_all_pinned_and_sum_is_not_100() -> None:
    reason = push_blocker([active(30, pinned=True), active(30, pinned=True)])

    assert reason is not None
    assert "60%" in reason


def test_push_blocked_without_active_offers() -> None:
    assert push_blocker([removed()]) == "The stream must have at least one active offer"


def test_push_blocked_when_an_active_offer_gets_zero_share() -> None:
    reason = push_blocker([active(60, pinned=True), active(40, pinned=True), active(0)])

    assert reason is not None
    assert "0%" in reason
