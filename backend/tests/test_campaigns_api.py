import re
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Campaign
from tests.fakes import FakeKeitaroClient


def payload(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "name": "  Spring promo  ",
        "geo": ["au", "MX", "AU"],
        "offer_id": 101,
        "domain_id": 1813,
        "group_id": 10332,
        "traffic_source_id": 836,
    }
    data.update(overrides)
    return data


async def test_creates_campaign_with_two_streams(
    client: AsyncClient, keitaro: FakeKeitaroClient, session: AsyncSession
) -> None:
    response = await client.post("/api/v1/campaigns", json=payload())

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "Spring promo"
    assert body["geo"] == ["AU", "MX"]
    assert len(body["stream_ids"]) == 2

    [campaign] = keitaro.created_campaigns
    # Our own alias, so a campaign whose create response is lost can be found.
    assert campaign.alias is not None
    assert re.fullmatch(r"[0-9a-f]{12}", campaign.alias)
    assert body["alias"] == campaign.alias
    assert campaign.model_dump(exclude={"alias"}) == {
        "name": "Spring promo",
        "type": "position",
        "group_id": 10332,
        "domain_id": 1813,
        "traffic_source_id": 836,
        "cost_type": "CPC",
        "cost_value": 0,
        "cost_currency": "USD",
        "state": "active",
    }

    geo_stream, offer_stream = (s.to_json() for s in keitaro.created_streams)
    assert geo_stream["campaign_id"] == body["id"]
    assert geo_stream["position"] == 1
    assert geo_stream["type"] == "regular"
    assert geo_stream["schema"] == "redirect"
    assert geo_stream["action_type"] == "http"
    assert geo_stream["action_payload"] == "https://google.com"
    assert geo_stream["filters"] == [{"name": "country", "mode": "accept", "payload": ["AU", "MX"]}]
    assert geo_stream["offers"] == []

    assert offer_stream["position"] == 2
    assert offer_stream["schema"] == "landings"
    assert offer_stream["filters"] == []
    assert offer_stream["offers"] == [{"offer_id": 101, "share": 100, "state": "active"}]

    stored = (await session.scalars(select(Campaign))).all()
    assert [(c.keitaro_id, c.name) for c in stored] == [(body["id"], "Spring promo")]


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"geo": []}, "geo"),
        ({"geo": ["XX"]}, "unknown country code"),
        ({"name": "   "}, "name"),
        ({"offer_id": 999}, "Offer 999 does not exist"),
        ({"offer_id": 203}, "Offer 203 is not active"),
        ({"domain_id": 1}, "Domain 1 does not exist"),
        ({"group_id": 1}, "Group 1 does not exist"),
        ({"traffic_source_id": 1}, "Traffic source 1 does not exist"),
    ],
)
async def test_rejects_invalid_input_without_calling_keitaro(
    client: AsyncClient, keitaro: FakeKeitaroClient, overrides: dict[str, Any], message: str
) -> None:
    response = await client.post("/api/v1/campaigns", json=payload(**overrides))

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"
    assert message in response.json()["error"]["message"]
    assert keitaro.created_campaigns == []


@pytest.mark.parametrize("failing_call", [1, 2])
async def test_deletes_campaign_when_a_stream_fails(
    client: AsyncClient, keitaro: FakeKeitaroClient, session: AsyncSession, failing_call: int
) -> None:
    keitaro.fail_stream_call = failing_call

    response = await client.post("/api/v1/campaigns", json=payload())

    assert response.status_code == 422
    assert response.json()["error"] == {
        "code": "keitaro_rejected",
        "message": "Keitaro: stream rejected",
    }
    assert keitaro.deleted_campaigns == [1001]
    assert (await session.scalars(select(Campaign))).all() == []
