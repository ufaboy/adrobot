from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Campaign, Offer, Stream


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

    async def get_stream(self, keitaro_id: int) -> Stream | None:
        stmt = (
            select(Stream)
            .where(Stream.keitaro_id == keitaro_id)
            .options(selectinload(Stream.offers))
            .execution_options(populate_existing=True)
        )
        return await self._session.scalar(stmt)

    async def offer_names(self, offer_ids: set[int]) -> dict[int, str]:
        if not offer_ids:
            return {}
        rows = await self._session.execute(
            select(Offer.id, Offer.name).where(Offer.id.in_(offer_ids))
        )
        return {offer_id: name for offer_id, name in rows.all()}
