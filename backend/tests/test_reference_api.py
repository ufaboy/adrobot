from httpx import AsyncClient

from tests.fakes import FakeKeitaroClient


async def test_reference_returns_lists_and_defaults(client: AsyncClient) -> None:
    response = await client.get("/api/v1/reference")

    assert response.status_code == 200
    body = response.json()
    assert body["domains"] == [{"id": 1813, "name": "kt-emulator.test"}]
    assert body["groups"] == [{"id": 10332, "name": "FORTESTS"}]
    assert body["traffic_sources"] == [{"id": 836, "name": "FORTESTS"}]
    # Configured default, and single-option fallbacks for the unset ones.
    assert body["defaults"] == {"domain_id": 1813, "group_id": 10332, "traffic_source_id": 836}
    assert {"code": "AU", "name": "Australia"} in body["countries"]


async def test_reference_is_cached_between_requests(
    client: AsyncClient, keitaro: FakeKeitaroClient
) -> None:
    await client.get("/api/v1/reference")
    await client.get("/api/v1/reference")

    assert keitaro.calls.count("list_domains") == 1
