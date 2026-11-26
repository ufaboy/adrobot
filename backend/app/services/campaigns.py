import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ValidationFailedError
from app.integrations.keitaro import KeitaroClient
from app.integrations.keitaro.schemas import (
    CampaignCreatePayload,
    KeitaroStreamFilter,
    KeitaroStreamOffer,
    StreamCreatePayload,
)
from app.models.campaign import Campaign
from app.repositories.campaigns import CampaignRepository
from app.schemas.campaigns import CampaignCreate, CampaignCreated
from app.services.offers import OfferService
from app.services.reference import ReferenceService

logger = logging.getLogger(__name__)

GEO_STREAM_NAME = "Geo redirect"
OFFER_STREAM_NAME = "Offers"


def build_geo_stream(campaign_id: int, geo: list[str], redirect_url: str) -> StreamCreatePayload:
    """Stream 1: visitors from the given countries are redirected to `redirect_url`."""
    return StreamCreatePayload(
        campaign_id=campaign_id,
        name=GEO_STREAM_NAME,
        type="regular",
        position=1,
        schema_="redirect",
        action_type="http",
        action_payload=redirect_url,
        filters=[KeitaroStreamFilter(name="country", mode="accept", payload=geo)],
    )


def build_offer_stream(campaign_id: int, offer_id: int) -> StreamCreatePayload:
    """Stream 2: everyone else goes to the offer."""
    return StreamCreatePayload(
        campaign_id=campaign_id,
        name=OFFER_STREAM_NAME,
        type="regular",
        position=2,
        schema_="landings",
        action_type="http",
        offers=[KeitaroStreamOffer(offer_id=offer_id, share=100, state="active")],
    )


class CampaignService:
    def __init__(
        self,
        session: AsyncSession,
        keitaro: KeitaroClient,
        offers: OfferService,
        reference: ReferenceService,
        google_url: str,
    ) -> None:
        self._session = session
        self._keitaro = keitaro
        self._offers = offers
        self._reference = reference
        self._google_url = google_url
        self._repo = CampaignRepository(session)

    async def create(self, data: CampaignCreate) -> CampaignCreated:
        await self._validate(data)

        campaign = await self._keitaro.create_campaign(
            CampaignCreatePayload(
                name=data.name,
                group_id=data.group_id,
                domain_id=data.domain_id,
                traffic_source_id=data.traffic_source_id,
            )
        )
        try:
            geo_stream = await self._keitaro.create_stream(
                build_geo_stream(campaign.id, data.geo, self._google_url)
            )
            offer_stream = await self._keitaro.create_stream(
                build_offer_stream(campaign.id, data.offer_id)
            )
            await self._repo.add(
                Campaign(keitaro_id=campaign.id, name=campaign.name, alias=campaign.alias)
            )
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            await self._compensate(campaign.id)
            raise

        return CampaignCreated(
            id=campaign.id,
            name=campaign.name,
            alias=campaign.alias,
            geo=data.geo,
            offer_id=data.offer_id,
            stream_ids=[geo_stream.id, offer_stream.id],
        )

    async def _validate(self, data: CampaignCreate) -> None:
        offer = await self._offers.get_fresh(data.offer_id)
        if offer is None:
            raise ValidationFailedError(f"Offer {data.offer_id} does not exist")
        if offer.state != "active":
            raise ValidationFailedError(f"Offer {data.offer_id} is not active")

        ref = await self._reference.keitaro_reference()
        checks = (
            ("Domain", data.domain_id, ref.domains),
            ("Group", data.group_id, ref.groups),
            ("Traffic source", data.traffic_source_id, ref.traffic_sources),
        )
        for label, item_id, items in checks:
            if item_id not in {item.id for item in items}:
                raise ValidationFailedError(f"{label} {item_id} does not exist")

    async def _compensate(self, campaign_id: int) -> None:
        """Delete a partially created campaign. Its streams are deleted with it."""
        try:
            await self._keitaro.delete_campaign(campaign_id)
        except Exception:
            logger.exception("Failed to delete partially created campaign %s", campaign_id)
        else:
            logger.info("Deleted partially created campaign %s", campaign_id)
