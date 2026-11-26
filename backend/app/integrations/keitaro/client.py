"""Async client for the Keitaro Admin API v1.

All Keitaro traffic goes through this module. Services depend on the `KeitaroClient`
protocol, so tests can substitute a fake implementation.
"""

import asyncio
import logging
from typing import Any, Protocol

import httpx
from fastapi import status
from pydantic import TypeAdapter, ValidationError

from app.core.errors import UpstreamError
from app.integrations.keitaro.schemas import (
    CampaignCreatePayload,
    KeitaroCampaign,
    KeitaroDomain,
    KeitaroGroup,
    KeitaroOffer,
    KeitaroStream,
    KeitaroStreamOffer,
    KeitaroTrafficSource,
    StreamCreatePayload,
)

logger = logging.getLogger(__name__)

_offers = TypeAdapter(list[KeitaroOffer])
_domains = TypeAdapter(list[KeitaroDomain])
_groups = TypeAdapter(list[KeitaroGroup])
_sources = TypeAdapter(list[KeitaroTrafficSource])
_campaigns = TypeAdapter(list[KeitaroCampaign])
_streams = TypeAdapter(list[KeitaroStream])
_campaign = TypeAdapter(KeitaroCampaign)
_stream = TypeAdapter(KeitaroStream)


class KeitaroError(UpstreamError):
    """Keitaro failed: a 5xx response or a response we could not understand (HTTP 502).

    `maybe_applied` is True when Keitaro may have executed the request even though we
    got no usable answer (a timeout after sending, a 5xx). Callers of non-idempotent
    requests use it to look for side effects.
    """

    def __init__(
        self, message: str, status_code: int | None = None, *, maybe_applied: bool = False
    ) -> None:
        super().__init__(f"Keitaro: {message}")
        self.upstream_status = status_code
        self.maybe_applied = maybe_applied


class KeitaroUnavailableError(KeitaroError):
    """Keitaro could not be reached or did not answer in time (HTTP 503)."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "keitaro_unavailable"


class KeitaroRejectedError(KeitaroError):
    """Keitaro answered with a 4xx; its message is shown to the user (HTTP 422)."""

    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = "keitaro_rejected"


# Requests that are safe to repeat when the first attempt may have been applied.
_IDEMPOTENT_METHODS = frozenset({"GET", "PUT", "DELETE"})
# Gateway errors: the request may or may not have reached Keitaro.
_RETRYABLE_STATUSES = frozenset({502, 503, 504})


class KeitaroClient(Protocol):
    async def list_offers(self) -> list[KeitaroOffer]: ...

    async def list_domains(self) -> list[KeitaroDomain]: ...

    async def list_campaign_groups(self) -> list[KeitaroGroup]: ...

    async def list_traffic_sources(self) -> list[KeitaroTrafficSource]: ...

    async def create_campaign(self, payload: CampaignCreatePayload) -> KeitaroCampaign: ...

    async def delete_campaign(self, campaign_id: int) -> None: ...

    async def create_stream(self, payload: StreamCreatePayload) -> KeitaroStream: ...

    async def list_campaigns(self) -> list[KeitaroCampaign]: ...

    async def get_campaign(self, campaign_id: int) -> KeitaroCampaign: ...

    async def list_streams(self, campaign_id: int) -> list[KeitaroStream]: ...

    async def update_stream_offers(
        self, stream_id: int, offers: list[KeitaroStreamOffer]
    ) -> KeitaroStream: ...


class HttpKeitaroClient:
    """`KeitaroClient` implementation over HTTP.

    Retry policy (at most one retry, since every call shows up in the API journal):
    - connection errors: the request never left, so any method is retried;
    - timeouts after sending and 502/503/504: only idempotent methods are retried;
      a POST is never repeated, it could create a duplicate.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        connect_timeout: float = 3.0,
        read_timeout: float = 10.0,
        retry_delay: float = 0.5,
    ) -> None:
        self._http = httpx.AsyncClient(
            base_url=f"{base_url.rstrip('/')}/v1",
            headers={"Api-Key": api_key},
            timeout=httpx.Timeout(read_timeout, connect=connect_timeout),
        )
        self._retry_delay = retry_delay

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _request(self, method: str, path: str, json: object | None = None) -> Any:
        try:
            return await self._attempt(method, path, json)
        except KeitaroError as exc:
            if not _should_retry(method, exc):
                raise
            logger.info("Retrying Keitaro %s %s after: %s", method, path, exc.message)
            await asyncio.sleep(self._retry_delay)
            return await self._attempt(method, path, json)

    async def _attempt(self, method: str, path: str, json: object | None) -> Any:
        try:
            response = await self._http.request(method, path, json=json)
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout) as exc:
            logger.warning("Keitaro unreachable: %s %s: %r", method, path, exc)
            raise KeitaroUnavailableError("service is unreachable") from exc
        except httpx.TimeoutException as exc:
            logger.warning("Keitaro timed out: %s %s: %r", method, path, exc)
            raise KeitaroUnavailableError("request timed out", maybe_applied=True) from exc
        except httpx.HTTPError as exc:
            logger.warning("Keitaro request failed: %s %s: %r", method, path, exc)
            raise KeitaroUnavailableError("connection failed", maybe_applied=True) from exc

        if response.is_error:
            message = _error_message(response)
            logger.warning(
                "Keitaro error %s on %s %s: %s", response.status_code, method, path, message
            )
            if response.is_client_error:
                raise KeitaroRejectedError(message, response.status_code)
            error_class = (
                KeitaroUnavailableError
                if response.status_code in _RETRYABLE_STATUSES
                else KeitaroError
            )
            raise error_class(message, response.status_code, maybe_applied=True)

        try:
            return response.json()
        except ValueError as exc:
            raise KeitaroError("unexpected response (not JSON)") from exc

    async def list_offers(self) -> list[KeitaroOffer]:
        return _parse(_offers, await self._request("GET", "/offers"))

    async def list_domains(self) -> list[KeitaroDomain]:
        return _parse(_domains, await self._request("GET", "/domains"))

    async def list_campaign_groups(self) -> list[KeitaroGroup]:
        data = await self._request("GET", "/groups?type=campaigns")
        return _parse(_groups, data)

    async def list_traffic_sources(self) -> list[KeitaroTrafficSource]:
        return _parse(_sources, await self._request("GET", "/traffic_sources"))

    async def create_campaign(self, payload: CampaignCreatePayload) -> KeitaroCampaign:
        data = await self._request("POST", "/campaigns", json=payload.model_dump(exclude_none=True))
        return _parse(_campaign, data)

    async def delete_campaign(self, campaign_id: int) -> None:
        """Delete a campaign; one that is already gone counts as deleted."""
        try:
            await self._request("DELETE", f"/campaigns/{campaign_id}")
        except KeitaroRejectedError as exc:
            if exc.upstream_status != status.HTTP_404_NOT_FOUND:
                raise

    async def create_stream(self, payload: StreamCreatePayload) -> KeitaroStream:
        data = await self._request("POST", "/streams", json=payload.to_json())
        return _parse(_stream, data)

    async def list_campaigns(self) -> list[KeitaroCampaign]:
        return _parse(_campaigns, await self._request("GET", "/campaigns"))

    async def get_campaign(self, campaign_id: int) -> KeitaroCampaign:
        data = await self._request("GET", f"/campaigns/{campaign_id}")
        return _parse(_campaign, data)

    async def list_streams(self, campaign_id: int) -> list[KeitaroStream]:
        data = await self._request("GET", f"/campaigns/{campaign_id}/streams")
        return _parse(_streams, data)

    async def update_stream_offers(
        self, stream_id: int, offers: list[KeitaroStreamOffer]
    ) -> KeitaroStream:
        """Replace the stream's offer list; other stream fields are left untouched."""
        body = {"offers": [o.model_dump() for o in offers]}
        data = await self._request("PUT", f"/streams/{stream_id}", json=body)
        return _parse(_stream, data)


def _parse[T](adapter: TypeAdapter[T], data: Any) -> T:
    try:
        return adapter.validate_python(data)
    except ValidationError as exc:
        logger.warning("Unexpected Keitaro response: %s", exc)
        raise KeitaroError("unexpected response format") from exc


def _should_retry(method: str, exc: KeitaroError) -> bool:
    if not isinstance(exc, KeitaroUnavailableError):
        return False
    return not exc.maybe_applied or method in _IDEMPOTENT_METHODS


def _error_message(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return f"HTTP {response.status_code}"
    if isinstance(body, dict):
        for key in ("error", "detail", "message"):
            if isinstance(body.get(key), str):
                return str(body[key])
    return f"HTTP {response.status_code}"
