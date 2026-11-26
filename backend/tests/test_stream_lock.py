from collections.abc import AsyncIterator
from datetime import timedelta

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.errors import ConflictError
from app.models import Campaign, Stream, StreamOffer
from app.repositories.streams import EditorRepository
from app.services.editor import EditorService
from app.services.offers import OfferService
from tests.fakes import FakeKeitaroClient

STREAM_KEITARO_ID = 777_001


@pytest.fixture
async def sessions(engine: AsyncEngine) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Sessions on separate connections with a committed stream; cleaned up after."""
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        session.add(
            Campaign(
                keitaro_id=777_000,
                name="Locked",
                alias="lock",
                streams=[
                    Stream(
                        keitaro_id=STREAM_KEITARO_ID,
                        name="Offers",
                        type="regular",
                        position=1,
                        offers=[StreamOffer(offer_id=101, position=1, state="active", share=100)],
                    )
                ],
            )
        )
        await session.commit()
    yield factory
    async with factory() as session:
        await session.execute(delete(Campaign).where(Campaign.keitaro_id == 777_000))
        await session.commit()


def editor(session: AsyncSession) -> EditorService:
    keitaro = FakeKeitaroClient()
    return EditorService(session, keitaro, OfferService(session, keitaro, timedelta(minutes=10)))


async def test_second_change_of_a_locked_stream_is_rejected(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    async with sessions() as holder, sessions() as other:
        # E.g. a push waiting for Keitaro holds the stream row.
        await EditorRepository(holder).get_stream(STREAM_KEITARO_ID, lock=True)

        with pytest.raises(ConflictError, match="still in progress"):
            await editor(other).cancel(STREAM_KEITARO_ID)

        await holder.rollback()

    # Once the first transaction ends, the stream can be changed again.
    async with sessions() as session:
        out = await editor(session).cancel(STREAM_KEITARO_ID)
        assert out.id == STREAM_KEITARO_ID
