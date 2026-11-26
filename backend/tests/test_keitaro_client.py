import json
from collections.abc import AsyncIterator

import httpx
import pytest
import respx

from app.integrations.keitaro import HttpKeitaroClient, KeitaroError
from app.integrations.keitaro.schemas import (
    CampaignCreatePayload,
    KeitaroStreamOffer,
    StreamCreatePayload,
)

BASE = "https://keitaro.example/admin_api"


@pytest.fixture
async def keitaro_client() -> AsyncIterator[HttpKeitaroClient]:
    client = HttpKeitaroClient(BASE, "secret-key")
    yield client
    await client.aclose()


@respx.mock
async def test_sends_api_key_and_parses_offers(keitaro_client: HttpKeitaroClient) -> None:
    route = respx.get(f"{BASE}/v1/offers").respond(
        json=[{"id": 1, "name": "Offer", "state": "active", "country": ["AU"], "extra": 1}]
    )

    offers = await keitaro_client.list_offers()

    assert route.calls.last.request.headers["Api-Key"] == "secret-key"
    assert offers[0].id == 1
    assert offers[0].country == ["AU"]


@respx.mock
async def test_stream_payload_uses_keitaro_field_names(keitaro_client: HttpKeitaroClient) -> None:
    route = respx.post(f"{BASE}/v1/streams").respond(
        json={
            "id": 7,
            "campaign_id": 3,
            "name": "Offers",
            "type": "regular",
            "position": 2,
            "state": "active",
            "schema": "landings",
            "offers": [{"id": 9, "offer_id": 5, "share": 100, "state": "active"}],
        }
    )

    stream = await keitaro_client.create_stream(
        StreamCreatePayload(
            campaign_id=3,
            name="Offers",
            position=2,
            schema_="landings",
            offers=[KeitaroStreamOffer(offer_id=5, share=100)],
        )
    )

    sent = json.loads(route.calls.last.request.content)
    assert sent["schema"] == "landings"
    assert "schema_" not in sent
    assert "action_payload" not in sent
    assert stream.schema_ == "landings"
    assert stream.offers[0].offer_id == 5


@respx.mock
async def test_error_body_becomes_keitaro_error(keitaro_client: HttpKeitaroClient) -> None:
    respx.post(f"{BASE}/v1/campaigns").respond(406, json={"error": "name is required"})

    with pytest.raises(KeitaroError) as exc_info:
        await keitaro_client.create_campaign(
            CampaignCreatePayload(name="x", group_id=1, domain_id=1, traffic_source_id=1)
        )

    assert exc_info.value.message == "Keitaro: name is required"
    assert exc_info.value.upstream_status == 406


@respx.mock
async def test_network_error_becomes_keitaro_error(keitaro_client: HttpKeitaroClient) -> None:
    respx.get(f"{BASE}/v1/domains").mock(side_effect=httpx.ConnectError("boom"))

    with pytest.raises(KeitaroError, match="unreachable"):
        await keitaro_client.list_domains()
