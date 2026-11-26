import logging
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.keitaro import KeitaroClient
from app.models.offer import Offer
from app.repositories.offers import OfferRepository

logger = logging.getLogger(__name__)


class OfferService:
    """Keeps the local offer catalog in sync with Keitaro and searches it."""

    def __init__(self, session: AsyncSession, keitaro: KeitaroClient, ttl: timedelta) -> None:
        self._session = session
        self._keitaro = keitaro
        self._ttl = ttl
        self._repo = OfferRepository(session)

    async def sync(self) -> int:
        """Reload the whole catalog from Keitaro. Returns the number of offers received."""
        remote = await self._keitaro.list_offers()
        offers = [
            Offer(id=o.id, name=o.name, state=o.state, countries=list(o.country)) for o in remote
        ]
        await self._repo.replace_catalog(offers, synced_at=datetime.now(UTC))
        await self._session.commit()
        logger.info("Offer catalog synced: %d offers", len(offers))
        return len(offers)

    async def ensure_fresh(self) -> None:
        """Sync the catalog if it was never loaded or is older than the TTL."""
        last = await self._repo.last_synced_at()
        if last is None or datetime.now(UTC) - last > self._ttl:
            await self.sync()

    async def search(self, query: str, *, limit: int = 20) -> Sequence[Offer]:
        await self.ensure_fresh()
        return await self._repo.search(query, limit=limit, active_only=True)

    async def get_fresh(self, offer_id: int) -> Offer | None:
        await self.ensure_fresh()
        return await self._repo.get(offer_id)
