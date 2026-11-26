"""Offer weight (share) rules. Pure functions, no I/O.

Shares are integer percentages.

- Removed offers have share 0 and are never pinned.
- Pinned active offers keep their share.
- The remainder `100 - sum(pinned)` is split evenly among unpinned active offers using the
  largest remainder method; leftover units go to the first offers by position, so the total
  is exactly 100 whenever at least one active offer is unpinned.
"""

from collections.abc import Sequence
from dataclasses import dataclass

TOTAL_SHARE = 100


class WeightError(ValueError):
    """The requested weights cannot be satisfied."""


@dataclass(frozen=True)
class WeightInput:
    active: bool
    pinned: bool
    share: int


def pinned_total(offers: Sequence[WeightInput]) -> int:
    return sum(o.share for o in offers if o.active and o.pinned)


def rebalance(offers: Sequence[WeightInput]) -> list[int]:
    """Return new shares for `offers` (in the same order).

    Raises `WeightError` if pinned shares exceed 100%.
    """
    pinned = pinned_total(offers)
    if pinned > TOTAL_SHARE:
        raise WeightError(f"Pinned shares add up to {pinned}%, more than {TOTAL_SHARE}%")

    unpinned = [i for i, o in enumerate(offers) if o.active and not o.pinned]
    remainder = TOTAL_SHARE - pinned
    base, extra = divmod(remainder, len(unpinned)) if unpinned else (0, 0)

    shares: list[int] = []
    rank = {index: n for n, index in enumerate(unpinned)}
    for i, offer in enumerate(offers):
        if not offer.active:
            shares.append(0)
        elif offer.pinned:
            shares.append(offer.share)
        else:
            shares.append(base + (1 if rank[i] < extra else 0))
    return shares


def push_blocker(offers: Sequence[WeightInput]) -> str | None:
    """Why the stream cannot be pushed to Keitaro, or None if it can."""
    active = [o for o in offers if o.active]
    if not active:
        return "The stream must have at least one active offer"
    total = sum(o.share for o in active)
    if total != TOTAL_SHARE:
        return f"Shares add up to {total}%, not {TOTAL_SHARE}%. Adjust or unpin a share."
    return None
