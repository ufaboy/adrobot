"""In-memory fake of the Keitaro API used by the tests."""

from dataclasses import dataclass, field

from app.integrations.keitaro import KeitaroError
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


@dataclass
class FakeKeitaroClient:
    offers: list[KeitaroOffer] = field(
        default_factory=lambda: [
            KeitaroOffer(id=101, name="Alpha Hair [MX]", state="active", country=["MX"]),
            KeitaroOffer(id=102, name="Beta Diet [AU]", state="active", country=["AU"]),
            KeitaroOffer(id=203, name="Gamma Archived", state="archived", country=[]),
        ]
    )
    domains: list[KeitaroDomain] = field(
        default_factory=lambda: [KeitaroDomain(id=1813, name="kt-emulator.test")]
    )
    groups: list[KeitaroGroup] = field(
        default_factory=lambda: [KeitaroGroup(id=10332, name="FORTESTS")]
    )
    traffic_sources: list[KeitaroTrafficSource] = field(
        default_factory=lambda: [KeitaroTrafficSource(id=836, name="FORTESTS")]
    )
    # Fail the N-th `create_stream` call (1-based); None means never fail.
    fail_stream_call: int | None = None

    calls: list[str] = field(default_factory=list)
    created_campaigns: list[CampaignCreatePayload] = field(default_factory=list)
    created_streams: list[StreamCreatePayload] = field(default_factory=list)
    deleted_campaigns: list[int] = field(default_factory=list)
    pushed: list[tuple[int, list[KeitaroStreamOffer]]] = field(default_factory=list)

    # State of the fake Keitaro instance.
    campaigns: dict[int, KeitaroCampaign] = field(default_factory=dict)
    streams: dict[int, KeitaroStream] = field(default_factory=dict)
    _next_id: int = 1000

    def _id(self) -> int:
        self._next_id += 1
        return self._next_id

    async def list_offers(self) -> list[KeitaroOffer]:
        self.calls.append("list_offers")
        return list(self.offers)

    async def list_domains(self) -> list[KeitaroDomain]:
        self.calls.append("list_domains")
        return list(self.domains)

    async def list_campaign_groups(self) -> list[KeitaroGroup]:
        self.calls.append("list_campaign_groups")
        return list(self.groups)

    async def list_traffic_sources(self) -> list[KeitaroTrafficSource]:
        self.calls.append("list_traffic_sources")
        return list(self.traffic_sources)

    async def create_campaign(self, payload: CampaignCreatePayload) -> KeitaroCampaign:
        self.calls.append("create_campaign")
        self.created_campaigns.append(payload)
        campaign = KeitaroCampaign(
            id=self._id(),
            alias="abc123",
            name=payload.name,
            state="active",
            group_id=payload.group_id,
            domain_id=payload.domain_id,
            traffic_source_id=payload.traffic_source_id,
        )
        self.campaigns[campaign.id] = campaign
        return campaign

    async def delete_campaign(self, campaign_id: int) -> None:
        self.calls.append("delete_campaign")
        self.deleted_campaigns.append(campaign_id)
        self.campaigns.pop(campaign_id, None)
        self.streams = {k: v for k, v in self.streams.items() if v.campaign_id != campaign_id}

    async def create_stream(self, payload: StreamCreatePayload) -> KeitaroStream:
        self.calls.append("create_stream")
        if self.fail_stream_call == len(self.created_streams) + 1:
            raise KeitaroError("stream rejected", 406)
        self.created_streams.append(payload)
        stream = KeitaroStream(
            id=self._id(),
            campaign_id=payload.campaign_id,
            name=payload.name,
            type=payload.type,
            position=payload.position,
            state=payload.state,
            schema_=payload.schema_,
            action_type=payload.action_type,
            action_payload=payload.action_payload,
            filters=payload.filters,
            offers=payload.offers,
        )
        self.streams[stream.id] = stream
        return stream

    # --- Editor ------------------------------------------------------------------------

    def add_campaign(self, name: str, *streams: tuple[str, list[tuple[int, int]]]) -> int:
        """Seed a campaign with streams given as (name, [(offer_id, share), ...])."""
        campaign_id = self._id()
        self.campaigns[campaign_id] = KeitaroCampaign(
            id=campaign_id, alias=f"alias{campaign_id}", name=name, state="active"
        )
        for position, (stream_name, offers) in enumerate(streams, start=1):
            stream_id = self._id()
            self.streams[stream_id] = KeitaroStream(
                id=stream_id,
                campaign_id=campaign_id,
                name=stream_name,
                type="regular",
                position=position,
                state="active",
                offers=[KeitaroStreamOffer(offer_id=o, share=s) for o, s in offers],
            )
        return campaign_id

    def set_offers(self, stream_id: int, offers: list[tuple[int, int]]) -> None:
        """Simulate a change made directly in Keitaro."""
        self.streams[stream_id] = self.streams[stream_id].model_copy(
            update={"offers": [KeitaroStreamOffer(offer_id=o, share=s) for o, s in offers]}
        )

    def stream_ids(self, campaign_id: int) -> list[int]:
        streams = [s for s in self.streams.values() if s.campaign_id == campaign_id]
        return [s.id for s in sorted(streams, key=lambda s: s.position)]

    async def list_campaigns(self) -> list[KeitaroCampaign]:
        self.calls.append("list_campaigns")
        return list(self.campaigns.values())

    async def get_campaign(self, campaign_id: int) -> KeitaroCampaign:
        self.calls.append("get_campaign")
        if campaign_id not in self.campaigns:
            raise KeitaroError("Campaign not found", 404)
        return self.campaigns[campaign_id]

    async def list_streams(self, campaign_id: int) -> list[KeitaroStream]:
        self.calls.append("list_streams")
        return [s for s in self.streams.values() if s.campaign_id == campaign_id]

    async def update_stream_offers(
        self, stream_id: int, offers: list[KeitaroStreamOffer]
    ) -> KeitaroStream:
        self.calls.append("update_stream_offers")
        self.pushed.append((stream_id, list(offers)))
        self.streams[stream_id] = self.streams[stream_id].model_copy(update={"offers": offers})
        return self.streams[stream_id]
