import os
from collections.abc import AsyncIterator

import pytest
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from app.api.deps import get_keitaro_client, get_reference_cache
from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.main import create_app
from app.models import Base
from app.services.reference import ReferenceCache
from tests.fakes import FakeKeitaroClient

load_dotenv()
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://app:app@localhost:5432/app_test"
)


@pytest.fixture(scope="session")
async def engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """A session bound to an outer transaction that is rolled back after the test.

    Commits inside the code under test become savepoints, so nothing persists.
    """
    async with engine.connect() as conn:
        transaction = await conn.begin()
        session = AsyncSession(
            bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()


@pytest.fixture
def keitaro() -> FakeKeitaroClient:
    return FakeKeitaroClient()


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        google_url="https://google.com",
        default_domain_id=1813,
        default_group_id=None,
        default_traffic_source_id=None,
        offers_cache_ttl_minutes=10,
    )


@pytest.fixture
async def client(
    session: AsyncSession, keitaro: FakeKeitaroClient, settings: Settings
) -> AsyncIterator[AsyncClient]:
    app = create_app()

    async def override_get_session() -> AsyncIterator[AsyncSession]:
        yield session

    cache = ReferenceCache(ttl_seconds=600)
    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_keitaro_client] = lambda: keitaro
    app.dependency_overrides[get_reference_cache] = lambda: cache
    app.dependency_overrides[get_settings] = lambda: settings

    # The lifespan (real Keitaro client, startup sync) is not run by ASGITransport.
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
