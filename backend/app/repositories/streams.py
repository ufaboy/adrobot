from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import ConflictError
from app.models import Campaign, Offer, Stream

# PostgreSQL "lock_not_available": raised by FOR UPDATE NOWAIT when the row is locked.
_LOCK_NOT_AVAILABLE = "55P03"


class EditorRepository:
    """Data access for campaign snapshots: campaigns with their streams and stream offers."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_campaign(self, keitaro_id: int) -> Campaign | None:
        stmt = (
            select(Campaign)
            .where(Campaign.keitaro_id == keitaro_id)
            .options(selectinload(Campaign.streams).selectinload(Stream.offers))
            .execution_options(populate_existing=True)
        )
        return await self._session.scalar(stmt)

    async def get_stream(self, keitaro_id: int, *, lock: bool = False) -> Stream | None:
        """Load a stream with its offers.

        With `lock`, the stream row stays locked until the transaction ends, so edits and
        pushes of one stream run one at a time. A stream that is already locked raises
        `ConflictError` at once instead of queueing a duplicate request behind it.
        """
        stmt = (
            select(Stream)
            .where(Stream.keitaro_id == keitaro_id)
            .options(selectinload(Stream.offers))
            .execution_options(populate_existing=True)
        )
        if lock:
            stmt = stmt.with_for_update(nowait=True, of=Stream)
        try:
            return await self._session.scalar(stmt)
        except DBAPIError as exc:
            if _sqlstate(exc) == _LOCK_NOT_AVAILABLE:
                raise ConflictError(
                    "Another action on this stream is still in progress; try again"
                ) from exc
            raise

    async def offer_names(self, offer_ids: set[int]) -> dict[int, str]:
        if not offer_ids:
            return {}
        rows = await self._session.execute(
            select(Offer.id, Offer.name).where(Offer.id.in_(offer_ids))
        )
        return {offer_id: name for offer_id, name in rows.all()}


def _sqlstate(exc: DBAPIError) -> str | None:
    code = getattr(exc.orig, "sqlstate", None) or getattr(exc.orig, "pgcode", None)
    return str(code) if code is not None else None
