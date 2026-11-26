import json
from collections.abc import AsyncIterator

import httpx
import pytest
import respx

from app.integrations.keitaro import (
    HttpKeitaroClient,
    KeitaroError,
    KeitaroRejectedError,
    KeitaroUnavailableError,
)
from app.integrations.keitaro.schemas import (
    CampaignCreatePayload,
    KeitaroStreamOffer,
    StreamCreatePayload,
)

BASE = "https://keitaro.example/admin_api"


@pytest.fixture
async def keitaro_client() -> AsyncIterator[HttpKeitaroClient]:
    client = HttpKeitaroClient(BASE, "secret-key", retry_delay=0)
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

    with pytest.raises(KeitaroRejectedError) as exc_info:
        await keitaro_client.create_campaign(
            CampaignCreatePayload(name="x", group_id=1, domain_id=1, traffic_source_id=1)
        )

    assert exc_info.value.message == "Keitaro: name is required"
    assert exc_info.value.upstream_status == 406


@respx.mock
async def test_network_error_becomes_keitaro_error(keitaro_client: HttpKeitaroClient) -> None:
    respx.get(f"{BASE}/v1/domains").mock(side_effect=httpx.ConnectError("boom"))

    with pytest.raises(KeitaroUnavailableError, match="unreachable"):
        await keitaro_client.list_domains()


# --- Retry policy ---------------------------------------------------------------------

CAMPAIGN = {"id": 5, "alias": "a1", "name": "x", "state": "active"}


def create_payload() -> CampaignCreatePayload:
    return CampaignCreatePayload(name="x", group_id=1, domain_id=1, traffic_source_id=1)


@respx.mock
async def test_connect_error_is_retried_even_for_post(keitaro_client: HttpKeitaroClient) -> None:
    route = respx.post(f"{BASE}/v1/campaigns").mock(
        side_effect=[httpx.ConnectError("refused"), httpx.Response(200, json=CAMPAIGN)]
    )

    campaign = await keitaro_client.create_campaign(create_payload())

    assert campaign.id == 5
    assert route.call_count == 2


@respx.mock
async def test_post_timeout_is_not_retried_and_may_be_applied(
    keitaro_client: HttpKeitaroClient,
) -> None:
    route = respx.post(f"{BASE}/v1/campaigns").mock(side_effect=httpx.ReadTimeout("slow"))

    with pytest.raises(KeitaroUnavailableError) as exc_info:
        await keitaro_client.create_campaign(create_payload())

    assert route.call_count == 1
    assert exc_info.value.maybe_applied
    assert exc_info.value.status_code == 503


@pytest.mark.parametrize(
    "first",
    [httpx.ReadTimeout("slow"), httpx.Response(503, json={"error": "busy"})],
    ids=["timeout", "503"],
)
@respx.mock
async def test_idempotent_requests_are_retried_once(
    keitaro_client: HttpKeitaroClient, first: Exception | httpx.Response
) -> None:
    ok = httpx.Response(
        200,
        json={
            "id": 7,
            "campaign_id": 3,
            "name": "s",
            "type": "regular",
            "position": 1,
            "state": "active",
        },
    )
    route = respx.put(f"{BASE}/v1/streams/7").mock(side_effect=[first, ok])

    stream = await keitaro_client.update_stream_offers(7, [])

    assert stream.id == 7
    assert route.call_count == 2


@respx.mock
async def test_gives_up_after_one_retry(keitaro_client: HttpKeitaroClient) -> None:
    route = respx.get(f"{BASE}/v1/campaigns").mock(side_effect=httpx.ReadTimeout("slow"))

    with pytest.raises(KeitaroUnavailableError, match="timed out"):
        await keitaro_client.list_campaigns()

    assert route.call_count == 2


@respx.mock
async def test_client_errors_are_not_retried(keitaro_client: HttpKeitaroClient) -> None:
    route = respx.get(f"{BASE}/v1/campaigns/9").respond(404, json={"error": "not found"})

    with pytest.raises(KeitaroRejectedError) as exc_info:
        await keitaro_client.get_campaign(9)

    assert route.call_count == 1
    assert exc_info.value.status_code == 422
    assert exc_info.value.code == "keitaro_rejected"


@respx.mock
async def test_server_error_is_upstream_error_and_not_retried(
    keitaro_client: HttpKeitaroClient,
) -> None:
    route = respx.get(f"{BASE}/v1/campaigns").respond(500, json={"error": "boom"})

    with pytest.raises(KeitaroError) as exc_info:
        await keitaro_client.list_campaigns()

    assert type(exc_info.value) is KeitaroError
    assert exc_info.value.status_code == 502
    assert route.call_count == 1


@respx.mock
async def test_unexpected_response_shape_is_upstream_error(
    keitaro_client: HttpKeitaroClient,
) -> None:
    respx.get(f"{BASE}/v1/campaigns").respond(200, json={"not": "a list"})

    with pytest.raises(KeitaroError, match="unexpected response format"):
        await keitaro_client.list_campaigns()


@respx.mock
async def test_deleting_a_missing_campaign_succeeds(keitaro_client: HttpKeitaroClient) -> None:
    respx.delete(f"{BASE}/v1/campaigns/5").respond(404, json={"error": "not found"})

    await keitaro_client.delete_campaign(5)
