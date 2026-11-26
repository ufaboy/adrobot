from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import String, cast, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.offer import OFFER_STATE_UNAVAILABLE, Offer


class OfferRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, offer_id: int) -> Offer | None:
        return await self._session.get(Offer, offer_id)

    async def last_synced_at(self) -> datetime | None:
        return await self._session.scalar(select(func.max(Offer.synced_at)))

    async def count_available(self) -> int:
        """Offers present in the last synced catalog (any state but unavailable)."""
        stmt = select(func.count()).where(Offer.state != OFFER_STATE_UNAVAILABLE)
        return await self._session.scalar(stmt) or 0

    async def replace_catalog(self, offers: Sequence[Offer], synced_at: datetime) -> None:
        """Upsert the given catalog; offers missing from it become unavailable."""
        if offers:
            stmt = insert(Offer).values(
                [
                    {
                        "id": o.id,
                        "name": o.name,
                        "state": o.state,
                        "countries": o.countries,
                        "synced_at": synced_at,
                    }
                    for o in offers
                ]
            )
            await self._session.execute(
                stmt.on_conflict_do_update(
                    index_elements=[Offer.id],
                    set_={
                        "name": stmt.excluded.name,
                        "state": stmt.excluded.state,
                        "countries": stmt.excluded.countries,
                        "synced_at": stmt.excluded.synced_at,
                    },
                )
            )
        await self._session.execute(
            update(Offer)
            .where(Offer.id.not_in([o.id for o in offers]))
            .values(state=OFFER_STATE_UNAVAILABLE, synced_at=synced_at)
        )

    async def search(self, query: str, *, limit: int, active_only: bool) -> Sequence[Offer]:
        """Find offers by id prefix or case-insensitive name substring."""
        stmt = select(Offer)
        query = query.strip()
        if query:
            pattern = f"%{_escape_like(query)}%"
            stmt = stmt.where(
                or_(
                    Offer.name.ilike(pattern, escape="\\"),
                    cast(Offer.id, String).like(f"{_escape_like(query)}%", escape="\\"),
                )
            )
        if active_only:
            stmt = stmt.where(Offer.state == "active")
        stmt = stmt.order_by(Offer.id.desc()).limit(limit)
        return (await self._session.scalars(stmt)).all()


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
