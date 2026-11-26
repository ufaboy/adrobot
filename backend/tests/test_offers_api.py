from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.keitaro.schemas import KeitaroOffer
from app.models import Offer
from tests.fakes import FakeKeitaroClient


async def test_search_syncs_catalog_and_returns_only_active(client: AsyncClient) -> None:
    response = await client.get("/api/v1/offers")

    assert response.status_code == 200
    assert [o["id"] for o in response.json()] == [102, 101]


async def test_search_by_name_is_case_insensitive(client: AsyncClient) -> None:
    response = await client.get("/api/v1/offers", params={"q": "hair"})

    assert [o["name"] for o in response.json()] == ["Alpha Hair [MX]"]


async def test_search_by_id_prefix(client: AsyncClient) -> None:
    response = await client.get("/api/v1/offers", params={"q": "10"})

    assert {o["id"] for o in response.json()} == {101, 102}


async def test_search_treats_like_wildcards_literally(client: AsyncClient) -> None:
    response = await client.get("/api/v1/offers", params={"q": "%"})

    assert response.json() == []


async def test_catalog_is_not_reloaded_while_fresh(
    client: AsyncClient, keitaro: FakeKeitaroClient
) -> None:
    await client.get("/api/v1/offers", params={"q": "a"})
    await client.get("/api/v1/offers", params={"q": "b"})

    assert keitaro.calls.count("list_offers") == 1


async def test_stale_catalog_is_reloaded(
    client: AsyncClient, keitaro: FakeKeitaroClient, session: AsyncSession
) -> None:
    await client.get("/api/v1/offers")
    await session.execute(update(Offer).values(synced_at=datetime.now(UTC) - timedelta(hours=1)))

    await client.get("/api/v1/offers")

    assert keitaro.calls.count("list_offers") == 2


async def test_refresh_marks_missing_offers_unavailable(
    client: AsyncClient, keitaro: FakeKeitaroClient, session: AsyncSession
) -> None:
    await client.get("/api/v1/offers")
    keitaro.offers = [KeitaroOffer(id=101, name="Alpha Hair v2", state="active", country=["MX"])]

    response = await client.post("/api/v1/offers/refresh")

    assert response.json() == {"count": 1}
    rows = (await session.execute(select(Offer.id, Offer.state))).all()
    states = {offer_id: state for offer_id, state in rows}
    assert states == {101: "active", 102: "unavailable", 203: "unavailable"}
    offer = await session.get(Offer, 101)
    assert offer is not None
    assert offer.name == "Alpha Hair v2"
