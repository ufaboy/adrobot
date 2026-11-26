import asyncio
import time
from dataclasses import dataclass

from app.core.config import Settings
from app.integrations.keitaro import KeitaroClient
from app.schemas.reference import CreatorDefaults, NamedItem, ReferenceData
from app.services.countries import list_countries


@dataclass(frozen=True)
class KeitaroReference:
    domains: list[NamedItem]
    groups: list[NamedItem]
    traffic_sources: list[NamedItem]


class ReferenceCache:
    """In-memory TTL cache of Keitaro reference lists (domains, groups, sources).

    They change rarely, and every Keitaro call is visible in the reviewer's journal.
    """

    def __init__(self, ttl_seconds: float) -> None:
        self._ttl = ttl_seconds
        self._value: KeitaroReference | None = None
        self._loaded_at = 0.0
        self._lock = asyncio.Lock()

    async def get(self, keitaro: KeitaroClient) -> KeitaroReference:
        async with self._lock:
            if self._value is None or time.monotonic() - self._loaded_at > self._ttl:
                self._value = await _load(keitaro)
                self._loaded_at = time.monotonic()
            return self._value


async def _load(keitaro: KeitaroClient) -> KeitaroReference:
    domains, groups, sources = await asyncio.gather(
        keitaro.list_domains(), keitaro.list_campaign_groups(), keitaro.list_traffic_sources()
    )
    return KeitaroReference(
        domains=[NamedItem(id=d.id, name=d.name) for d in domains if d.state == "active"],
        groups=[NamedItem(id=g.id, name=g.name) for g in groups],
        traffic_sources=[NamedItem(id=s.id, name=s.name) for s in sources if s.state == "active"],
    )


class ReferenceService:
    def __init__(self, keitaro: KeitaroClient, cache: ReferenceCache, settings: Settings) -> None:
        self._keitaro = keitaro
        self._cache = cache
        self._settings = settings

    async def keitaro_reference(self) -> KeitaroReference:
        return await self._cache.get(self._keitaro)

    async def creator_reference(self) -> ReferenceData:
        ref = await self.keitaro_reference()
        return ReferenceData(
            domains=ref.domains,
            groups=ref.groups,
            traffic_sources=ref.traffic_sources,
            countries=list(list_countries()),
            defaults=CreatorDefaults(
                domain_id=_default(self._settings.default_domain_id, ref.domains),
                group_id=_default(self._settings.default_group_id, ref.groups),
                traffic_source_id=_default(
                    self._settings.default_traffic_source_id, ref.traffic_sources
                ),
            ),
        )


def _default(configured: int | None, items: list[NamedItem]) -> int | None:
    """The configured id if it exists, otherwise the only available option."""
    ids = {item.id for item in items}
    if configured is not None and configured in ids:
        return configured
    return items[0].id if len(items) == 1 else None
