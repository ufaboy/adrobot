import asyncio
from collections.abc import AsyncIterator
from datetime import timedelta

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.integrations.keitaro.schemas import KeitaroOffer
from app.models import Offer
from app.services.offers import OfferService
from tests.fakes import FakeKeitaroClient


class SlowKeitaro(FakeKeitaroClient):
    """Keitaro whose offer list takes a moment, so concurrent requests overlap."""

    async def list_offers(self) -> list[KeitaroOffer]:
        await asyncio.sleep(0.05)
        return await super().list_offers()


@pytest.fixture
async def committing_sessions(
    engine: AsyncEngine,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Sessions on separate connections that really commit; the catalog is wiped after."""
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    async with factory() as session:
        await session.execute(delete(Offer))
        await session.commit()


async def test_concurrent_requests_on_a_stale_catalog_sync_once(
    committing_sessions: async_sessionmaker[AsyncSession],
) -> None:
    keitaro = SlowKeitaro()

    async def search() -> int:
        async with committing_sessions() as session:
            service = OfferService(session, keitaro, timedelta(minutes=10))
            return len(await service.search(""))

    results = await asyncio.gather(*(search() for _ in range(5)))

    assert keitaro.calls.count("list_offers") == 1
    assert results == [2] * 5


async def test_concurrent_refreshes_call_keitaro_once(
    committing_sessions: async_sessionmaker[AsyncSession],
) -> None:
    keitaro = SlowKeitaro()

    async def refresh() -> int:
        async with committing_sessions() as session:
            return await OfferService(session, keitaro, timedelta(minutes=10)).sync()

    counts = await asyncio.gather(refresh(), refresh(), refresh())

    assert keitaro.calls.count("list_offers") == 1
    assert list(counts) == [3, 3, 3]


async def test_a_later_refresh_reloads_again(
    committing_sessions: async_sessionmaker[AsyncSession],
) -> None:
    keitaro = SlowKeitaro()
    async with committing_sessions() as session:
        service = OfferService(session, keitaro, timedelta(minutes=10))
        await service.sync()
        await service.sync()

    assert keitaro.calls.count("list_offers") == 2
