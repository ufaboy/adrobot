"""Async client for the Keitaro Admin API v1.

All Keitaro traffic goes through this module. Services depend on the `KeitaroClient`
protocol, so tests can substitute a fake implementation.
"""

import logging
from typing import Any, Protocol

import httpx
from pydantic import TypeAdapter

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


class KeitaroError(UpstreamError):
    """Keitaro rejected a request or could not be reached."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(f"Keitaro: {message}")
        self.upstream_status = status_code


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
    """`KeitaroClient` implementation over HTTP."""

    def __init__(self, base_url: str, api_key: str, *, timeout: float = 15.0) -> None:
        self._http = httpx.AsyncClient(
            base_url=f"{base_url.rstrip('/')}/v1",
            headers={"Api-Key": api_key},
            timeout=timeout,
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _request(self, method: str, path: str, json: object | None = None) -> Any:
        try:
            response = await self._http.request(method, path, json=json)
        except httpx.HTTPError as exc:
            logger.warning("Keitaro request failed: %s %s: %s", method, path, exc)
            raise KeitaroError("service is unreachable") from exc

        if response.is_error:
            message = _error_message(response)
            logger.warning(
                "Keitaro error %s on %s %s: %s", response.status_code, method, path, message
            )
            raise KeitaroError(message, response.status_code)
        return response.json()

    async def list_offers(self) -> list[KeitaroOffer]:
        return _offers.validate_python(await self._request("GET", "/offers"))

    async def list_domains(self) -> list[KeitaroDomain]:
        return _domains.validate_python(await self._request("GET", "/domains"))

    async def list_campaign_groups(self) -> list[KeitaroGroup]:
        data = await self._request("GET", "/groups?type=campaigns")
        return _groups.validate_python(data)

    async def list_traffic_sources(self) -> list[KeitaroTrafficSource]:
        return _sources.validate_python(await self._request("GET", "/traffic_sources"))

    async def create_campaign(self, payload: CampaignCreatePayload) -> KeitaroCampaign:
        data = await self._request("POST", "/campaigns", json=payload.model_dump())
        return KeitaroCampaign.model_validate(data)

    async def delete_campaign(self, campaign_id: int) -> None:
        await self._request("DELETE", f"/campaigns/{campaign_id}")

    async def create_stream(self, payload: StreamCreatePayload) -> KeitaroStream:
        data = await self._request("POST", "/streams", json=payload.to_json())
        return KeitaroStream.model_validate(data)

    async def list_campaigns(self) -> list[KeitaroCampaign]:
        return _campaigns.validate_python(await self._request("GET", "/campaigns"))

    async def get_campaign(self, campaign_id: int) -> KeitaroCampaign:
        data = await self._request("GET", f"/campaigns/{campaign_id}")
        return KeitaroCampaign.model_validate(data)

    async def list_streams(self, campaign_id: int) -> list[KeitaroStream]:
        data = await self._request("GET", f"/campaigns/{campaign_id}/streams")
        return _streams.validate_python(data)

    async def update_stream_offers(
        self, stream_id: int, offers: list[KeitaroStreamOffer]
    ) -> KeitaroStream:
        """Replace the stream's offer list; other stream fields are left untouched."""
        body = {"offers": [o.model_dump() for o in offers]}
        data = await self._request("PUT", f"/streams/{stream_id}", json=body)
        return KeitaroStream.model_validate(data)


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
