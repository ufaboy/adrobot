"""Campaign creation when Keitaro's answer is lost, and idempotent retries."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, ValidationFailedError
from app.integrations.keitaro import KeitaroError, KeitaroUnavailableError
from app.models import Campaign
from app.services.idempotency import IdempotencyStore
from tests.fakes import FakeKeitaroClient
from tests.test_campaigns_api import payload

TIMEOUT = KeitaroUnavailableError("request timed out", maybe_applied=True)


# --- Lost create response ---------------------------------------------------------------


async def test_lost_campaign_is_found_by_alias_and_deleted(
    client: AsyncClient, keitaro: FakeKeitaroClient, session: AsyncSession
) -> None:
    keitaro.create_campaign_error = TIMEOUT
    keitaro.create_applies_before_error = True

    response = await client.post("/api/v1/campaigns", json=payload())

    assert response.status_code == 503
    assert response.json()["error"] == {
        "code": "keitaro_unavailable",
        "message": "Keitaro: Request timed out. Nothing was created; try again",
    }
    [created] = keitaro.created_campaigns
    assert keitaro.deleted_campaigns == [1001]
    assert keitaro.campaigns == {}
    assert created.alias is not None
    assert keitaro.created_streams == []
    assert (await session.scalars(select(Campaign))).all() == []


async def test_lost_response_without_a_campaign_deletes_nothing(
    client: AsyncClient, keitaro: FakeKeitaroClient
) -> None:
    keitaro.create_campaign_error = TIMEOUT

    response = await client.post("/api/v1/campaigns", json=payload())

    assert response.status_code == 503
    assert "Nothing was created" in response.json()["error"]["message"]
    assert keitaro.calls[-1] == "list_campaigns"
    assert keitaro.deleted_campaigns == []


async def test_failed_lookup_reports_the_alias(
    client: AsyncClient, keitaro: FakeKeitaroClient
) -> None:
    keitaro.create_campaign_error = TIMEOUT
    keitaro.create_applies_before_error = True
    keitaro.list_campaigns_error = KeitaroUnavailableError("service is unreachable")

    response = await client.post("/api/v1/campaigns", json=payload())

    [created] = keitaro.created_campaigns
    assert response.status_code == 503
    assert (
        f"may have been created with alias {created.alias}" in (response.json()["error"]["message"])
    )


async def test_rejected_create_does_not_look_for_a_lost_campaign(
    client: AsyncClient, keitaro: FakeKeitaroClient
) -> None:
    keitaro.create_campaign_error = KeitaroError("bad payload", 400)

    await client.post("/api/v1/campaigns", json=payload())

    assert "list_campaigns" not in keitaro.calls


# --- Idempotency-Key ----------------------------------------------------------------------


async def test_repeated_key_replays_the_result_without_calling_keitaro(
    client: AsyncClient, keitaro: FakeKeitaroClient
) -> None:
    headers = {"Idempotency-Key": "form-1"}

    first = await client.post("/api/v1/campaigns", json=payload(), headers=headers)
    second = await client.post("/api/v1/campaigns", json=payload(), headers=headers)

    assert first.status_code == second.status_code == 201
    assert second.json() == first.json()
    assert keitaro.calls.count("create_campaign") == 1


async def test_key_reused_with_another_body_is_rejected(
    client: AsyncClient, keitaro: FakeKeitaroClient
) -> None:
    headers = {"Idempotency-Key": "form-1"}
    await client.post("/api/v1/campaigns", json=payload(), headers=headers)

    response = await client.post("/api/v1/campaigns", json=payload(name="Other"), headers=headers)

    assert response.status_code == 422
    assert "Idempotency-Key" in response.json()["error"]["message"]
    assert keitaro.calls.count("create_campaign") == 1


async def test_failed_request_can_be_retried_with_the_same_key(
    client: AsyncClient, keitaro: FakeKeitaroClient
) -> None:
    headers = {"Idempotency-Key": "form-1"}
    keitaro.fail_stream_call = 1
    failed = await client.post("/api/v1/campaigns", json=payload(), headers=headers)

    keitaro.fail_stream_call = None
    retried = await client.post("/api/v1/campaigns", json=payload(), headers=headers)

    assert failed.status_code == 422
    assert retried.status_code == 201
    assert keitaro.calls.count("create_campaign") == 2


async def test_without_a_key_every_request_creates(
    client: AsyncClient, keitaro: FakeKeitaroClient
) -> None:
    await client.post("/api/v1/campaigns", json=payload())
    await client.post("/api/v1/campaigns", json=payload())

    assert keitaro.calls.count("create_campaign") == 2


def test_store_rejects_a_key_that_is_still_in_progress() -> None:
    store = IdempotencyStore[str]()
    assert store.begin("k", "body") is None

    with pytest.raises(ConflictError):
        store.begin("k", "body")

    store.complete("k", "done")
    assert store.begin("k", "body") == "done"
    with pytest.raises(ValidationFailedError):
        store.begin("k", "other body")


def test_store_forgets_expired_keys() -> None:
    store = IdempotencyStore[str](ttl_seconds=-1)
    store.begin("k", "body")
    store.complete("k", "done")

    assert store.begin("k", "body") is None
