"""End-to-end editor scenarios over the HTTP API, mirroring the reference video."""

from typing import Any

import pytest
from httpx import AsyncClient

from app.integrations.keitaro import KeitaroUnavailableError
from app.integrations.keitaro.schemas import KeitaroOffer
from tests.fakes import FakeKeitaroClient

# Offers 101 and 102 are active in the fake catalog; 203 is archived.
pytestmark = pytest.mark.usefixtures("catalog")


@pytest.fixture
async def catalog(client: AsyncClient) -> None:
    await client.post("/api/v1/offers/refresh")


@pytest.fixture
def campaign_id(keitaro: FakeKeitaroClient) -> int:
    keitaro.offers += [
        KeitaroOffer(id=301, name="Offer 301", state="active"),
        KeitaroOffer(id=302, name="Offer 302", state="active"),
        KeitaroOffer(id=303, name="Offer 303", state="active"),
    ]
    return keitaro.add_campaign(
        "Spring promo",
        ("Geo redirect", []),
        ("Offers", [(301, 34), (302, 33), (303, 33)]),
    )


@pytest.fixture
async def stream_id(client: AsyncClient, keitaro: FakeKeitaroClient, campaign_id: int) -> int:
    await client.post("/api/v1/offers/refresh")
    response = await client.get(f"/api/v1/campaigns/{campaign_id}")
    assert response.status_code == 200, response.text
    return keitaro.stream_ids(campaign_id)[1]


def shares(stream: dict[str, Any]) -> list[tuple[int, str, int, bool]]:
    return [(o["offer_id"], o["state"], o["share"], o["pinned"]) for o in stream["offers"]]


async def test_lists_campaigns_from_keitaro(client: AsyncClient, campaign_id: int) -> None:
    response = await client.get("/api/v1/campaigns")

    assert [c["id"] for c in response.json()] == [campaign_id]


async def test_first_open_fetches_streams(
    client: AsyncClient, keitaro: FakeKeitaroClient, campaign_id: int
) -> None:
    await client.post("/api/v1/offers/refresh")  # pick up the offers seeded by `campaign_id`

    response = await client.get(f"/api/v1/campaigns/{campaign_id}")

    body = response.json()
    geo, offers = body["streams"]
    assert body["name"] == "Spring promo"
    assert geo["editable"] is False
    assert geo["offers"] == []
    assert offers["editable"] is True
    assert offers["dirty"] is False
    assert shares(offers) == [
        (301, "active", 34, False),
        (302, "active", 33, False),
        (303, "active", 33, False),
    ]
    assert offers["offers"][0]["name"] == "Offer 301"

    # Opening again uses the local snapshot, not Keitaro.
    await client.get(f"/api/v1/campaigns/{campaign_id}")
    assert keitaro.calls.count("list_streams") == 1


async def test_unknown_campaign_returns_keitaro_error(client: AsyncClient) -> None:
    response = await client.get("/api/v1/campaigns/999999")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "keitaro_rejected"
    assert "Campaign not found" in response.json()["error"]["message"]


async def test_add_offer_rebalances_and_push_publishes(
    client: AsyncClient, keitaro: FakeKeitaroClient, stream_id: int
) -> None:
    response = await client.post(f"/api/v1/streams/{stream_id}/offers", json={"offer_id": 101})

    stream = response.json()
    assert shares(stream)[-1] == (101, "active", 25, False)
    assert [o["share"] for o in stream["offers"]] == [25, 25, 25, 25]
    assert stream["dirty"] is True
    assert stream["offers"][-1]["is_new"] is True
    assert keitaro.pushed == []  # nothing reaches Keitaro before Push

    pushed = (await client.post(f"/api/v1/streams/{stream_id}/push")).json()

    assert pushed["dirty"] is False
    assert [(o.offer_id, o.share) for o in keitaro.pushed[-1][1]] == [
        (301, 25),
        (302, 25),
        (303, 25),
        (101, 25),
    ]


async def test_cancel_drops_unpublished_additions(client: AsyncClient, stream_id: int) -> None:
    await client.post(f"/api/v1/streams/{stream_id}/offers", json={"offer_id": 101})

    stream = (await client.post(f"/api/v1/streams/{stream_id}/cancel")).json()

    assert stream["dirty"] is False
    assert [o["offer_id"] for o in stream["offers"]] == [301, 302, 303]
    assert [o["share"] for o in stream["offers"]] == [34, 33, 33]


async def test_remove_push_and_bring_back(
    client: AsyncClient, keitaro: FakeKeitaroClient, stream_id: int
) -> None:
    removed = (await client.post(f"/api/v1/streams/{stream_id}/offers/302/remove")).json()
    assert shares(removed) == [
        (301, "active", 50, False),
        (302, "removed", 0, False),
        (303, "active", 50, False),
    ]

    await client.post(f"/api/v1/streams/{stream_id}/push")
    assert [o.offer_id for o in keitaro.pushed[-1][1]] == [301, 303]

    back = (await client.post(f"/api/v1/streams/{stream_id}/offers/302/bring-back")).json()
    assert back["dirty"] is True
    assert [o["share"] for o in back["offers"]] == [34, 33, 33]


async def test_adding_a_removed_offer_suggests_bring_back(
    client: AsyncClient, stream_id: int
) -> None:
    await client.post(f"/api/v1/streams/{stream_id}/offers/302/remove")

    response = await client.post(f"/api/v1/streams/{stream_id}/offers", json={"offer_id": 302})

    assert response.status_code == 409
    assert "bring it back" in response.json()["error"]["message"]


async def test_adding_duplicate_or_inactive_offer_is_rejected(
    client: AsyncClient, stream_id: int
) -> None:
    duplicate = await client.post(f"/api/v1/streams/{stream_id}/offers", json={"offer_id": 301})
    inactive = await client.post(f"/api/v1/streams/{stream_id}/offers", json={"offer_id": 203})

    assert duplicate.status_code == 409
    assert inactive.status_code == 422


async def test_offers_removed_in_keitaro_become_removed_on_fetch(
    client: AsyncClient, keitaro: FakeKeitaroClient, campaign_id: int, stream_id: int
) -> None:
    keitaro.set_offers(stream_id, [(301, 100)])

    body = (await client.post(f"/api/v1/campaigns/{campaign_id}/fetch")).json()

    stream = body["streams"][1]
    assert shares(stream) == [
        (301, "active", 100, False),
        (302, "removed", 0, False),
        (303, "removed", 0, False),
    ]
    assert stream["dirty"] is False


async def test_pinned_share_survives_rebalancing_and_push(
    client: AsyncClient, keitaro: FakeKeitaroClient, campaign_id: int, stream_id: int
) -> None:
    await client.post(f"/api/v1/streams/{stream_id}/offers", json={"offer_id": 101})
    pinned = (
        await client.put(f"/api/v1/streams/{stream_id}/offers/301/share", json={"share": 25})
    ).json()
    assert shares(pinned)[0] == (301, "active", 25, True)

    after_remove = (await client.post(f"/api/v1/streams/{stream_id}/offers/302/remove")).json()
    assert [o["share"] for o in after_remove["offers"]] == [25, 0, 38, 37]

    await client.post(f"/api/v1/streams/{stream_id}/push")
    refetched = (await client.post(f"/api/v1/campaigns/{campaign_id}/fetch")).json()["streams"][1]

    assert shares(refetched)[0] == (301, "active", 25, True)
    assert sum(o["share"] for o in refetched["offers"]) == 100


async def test_pins_over_100_are_rejected_and_nothing_changes(
    client: AsyncClient, stream_id: int
) -> None:
    await client.put(f"/api/v1/streams/{stream_id}/offers/301/share", json={"share": 70})

    response = await client.put(f"/api/v1/streams/{stream_id}/offers/302/share", json={"share": 40})

    assert response.status_code == 422
    assert "110%" in response.json()["error"]["message"]


async def test_push_blocked_when_all_pinned_shares_do_not_sum_to_100(
    client: AsyncClient, keitaro: FakeKeitaroClient, stream_id: int
) -> None:
    for offer_id in (301, 302, 303):
        stream = (
            await client.put(
                f"/api/v1/streams/{stream_id}/offers/{offer_id}/share", json={"share": 30}
            )
        ).json()
    assert stream["push_blocker"] == "Shares add up to 90%, not 100%. Adjust or unpin a share."

    response = await client.post(f"/api/v1/streams/{stream_id}/push")

    assert response.status_code == 422
    assert keitaro.pushed == []


async def test_read_only_stream_cannot_be_edited(
    client: AsyncClient, keitaro: FakeKeitaroClient, campaign_id: int, stream_id: int
) -> None:
    geo_stream = keitaro.stream_ids(campaign_id)[0]

    response = await client.post(f"/api/v1/streams/{geo_stream}/offers", json={"offer_id": 101})

    assert response.status_code == 422
    assert "read-only" in response.json()["error"]["message"]


async def test_push_without_changes_is_rejected(client: AsyncClient, stream_id: int) -> None:
    response = await client.post(f"/api/v1/streams/{stream_id}/push")

    assert response.status_code == 409


async def test_push_is_refused_when_the_stream_changed_in_keitaro(
    client: AsyncClient, keitaro: FakeKeitaroClient, stream_id: int
) -> None:
    await client.post(f"/api/v1/streams/{stream_id}/offers/302/remove")
    keitaro.set_offers(stream_id, [(301, 60), (302, 40)])  # someone edited it in Keitaro

    response = await client.post(f"/api/v1/streams/{stream_id}/push")

    assert response.status_code == 409
    assert "changed in Keitaro" in response.json()["error"]["message"]
    assert keitaro.pushed == []
    stream = await client.get(f"/api/v1/campaigns/{keitaro.streams[stream_id].campaign_id}")
    assert stream.json()["streams"][1]["dirty"] is True


async def test_push_already_applied_in_keitaro_is_recorded_without_sending(
    client: AsyncClient, keitaro: FakeKeitaroClient, stream_id: int
) -> None:
    await client.post(f"/api/v1/streams/{stream_id}/offers/302/remove")
    # An earlier push reached Keitaro, but its response was lost.
    keitaro.set_offers(stream_id, [(301, 50), (303, 50)])

    response = await client.post(f"/api/v1/streams/{stream_id}/push")

    assert response.status_code == 200, response.text
    assert response.json()["dirty"] is False
    assert keitaro.pushed == []


async def test_failed_push_keeps_the_draft(
    client: AsyncClient, keitaro: FakeKeitaroClient, stream_id: int
) -> None:
    await client.post(f"/api/v1/streams/{stream_id}/offers/302/remove")
    keitaro.update_stream_error = KeitaroUnavailableError("request timed out", maybe_applied=True)

    failed = await client.post(f"/api/v1/streams/{stream_id}/push")

    assert failed.status_code == 503
    keitaro.update_stream_error = None
    retried = await client.post(f"/api/v1/streams/{stream_id}/push")
    assert retried.status_code == 200, retried.text
    assert [(o.offer_id, o.share) for o in keitaro.pushed[-1][1]] == [(301, 50), (303, 50)]


async def test_push_to_a_stream_deleted_in_keitaro_asks_to_fetch(
    client: AsyncClient, keitaro: FakeKeitaroClient, stream_id: int
) -> None:
    await client.post(f"/api/v1/streams/{stream_id}/offers/302/remove")
    del keitaro.streams[stream_id]

    response = await client.post(f"/api/v1/streams/{stream_id}/push")

    assert response.status_code == 409
    assert "deleted in Keitaro" in response.json()["error"]["message"]


async def test_offer_inactive_in_the_catalog_cannot_be_brought_back(
    client: AsyncClient, keitaro: FakeKeitaroClient, stream_id: int
) -> None:
    await client.post(f"/api/v1/streams/{stream_id}/offers/302/remove")
    keitaro.offers = [
        o.model_copy(update={"state": "archived"}) if o.id == 302 else o for o in keitaro.offers
    ]
    await client.post("/api/v1/offers/refresh")

    response = await client.post(f"/api/v1/streams/{stream_id}/offers/302/bring-back")

    assert response.status_code == 422
    assert "not active" in response.json()["error"]["message"]


async def test_fetch_rejects_a_stream_listing_an_offer_twice(
    client: AsyncClient, keitaro: FakeKeitaroClient, campaign_id: int, stream_id: int
) -> None:
    keitaro.set_offers(stream_id, [(301, 50), (302, 25), (301, 25)])

    response = await client.post(f"/api/v1/campaigns/{campaign_id}/fetch")

    assert response.status_code == 422
    assert "offer 301 more than once" in response.json()["error"]["message"]
    snapshot = (await client.get(f"/api/v1/campaigns/{campaign_id}")).json()
    assert [o["offer_id"] for o in snapshot["streams"][1]["offers"]] == [301, 302, 303]
