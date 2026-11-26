import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ValidationFailedError
from app.integrations.keitaro import KeitaroClient, KeitaroError
from app.integrations.keitaro.schemas import (
    CampaignCreatePayload,
    KeitaroStreamFilter,
    KeitaroStreamOffer,
    StreamCreatePayload,
)
from app.models.campaign import Campaign
from app.repositories.campaigns import CampaignRepository
from app.schemas.campaigns import CampaignCreate, CampaignCreated
from app.services.idempotency import IdempotencyStore
from app.services.offers import OfferService
from app.services.reference import ReferenceService

logger = logging.getLogger(__name__)

GEO_STREAM_NAME = "Geo redirect"
OFFER_STREAM_NAME = "Offers"

CampaignIdempotency = IdempotencyStore[CampaignCreated]


def new_alias() -> str:
    """A unique campaign alias, so a campaign can be found if the create response is lost."""
    return uuid.uuid4().hex[:12]


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
        idempotency: CampaignIdempotency,
    ) -> None:
        self._session = session
        self._keitaro = keitaro
        self._offers = offers
        self._reference = reference
        self._google_url = google_url
        self._idempotency = idempotency
        self._repo = CampaignRepository(session)

    async def create(
        self, data: CampaignCreate, idempotency_key: str | None = None
    ) -> CampaignCreated:
        """Create the campaign; a repeated `idempotency_key` returns the first result."""
        if idempotency_key is None:
            return await self._create(data)

        stored = self._idempotency.begin(idempotency_key, data.model_dump_json())
        if stored is not None:
            logger.info("Replaying campaign creation for idempotency key %s", idempotency_key)
            return stored
        try:
            created = await self._create(data)
        except BaseException:
            self._idempotency.abandon(idempotency_key)
            raise
        self._idempotency.complete(idempotency_key, created)
        return created

    async def _create(self, data: CampaignCreate) -> CampaignCreated:
        await self._validate(data)

        alias = new_alias()
        try:
            campaign = await self._keitaro.create_campaign(
                CampaignCreatePayload(
                    name=data.name,
                    alias=alias,
                    group_id=data.group_id,
                    domain_id=data.domain_id,
                    traffic_source_id=data.traffic_source_id,
                )
            )
        except KeitaroError as exc:
            if exc.maybe_applied:
                await self._remove_lost_campaign(alias, exc)
            raise
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

    async def _remove_lost_campaign(self, alias: str, error: KeitaroError) -> None:
        """Keitaro may have created the campaign although we got no answer: find it by
        alias and delete it, so the outcome is all-or-nothing. Always raises."""
        error_class = type(error)
        try:
            campaigns = await self._keitaro.list_campaigns()
        except KeitaroError as exc:
            raise error_class(
                f"{_reason(error)}. The campaign may have been created with alias {alias}; "
                "check the campaign list",
                error.upstream_status,
            ) from exc

        lost = next((c for c in campaigns if c.alias == alias), None)
        if lost is not None:
            try:
                await self._keitaro.delete_campaign(lost.id)
            except KeitaroError as exc:
                raise error_class(
                    f"{_reason(error)}. Campaign {lost.id} (alias {alias}) was created but "
                    "could not be deleted; delete it in Keitaro",
                    error.upstream_status,
                ) from exc
            logger.info("Deleted campaign %s whose create response was lost", lost.id)

        raise error_class(
            f"{_reason(error)}. Nothing was created; try again", error.upstream_status
        ) from error

    async def _compensate(self, campaign_id: int) -> None:
        """Delete a partially created campaign. Its streams are deleted with it."""
        try:
            await self._keitaro.delete_campaign(campaign_id)
        except Exception:
            logger.exception("Failed to delete partially created campaign %s", campaign_id)
        else:
            logger.info("Deleted partially created campaign %s", campaign_id)


def _reason(error: KeitaroError) -> str:
    """The Keitaro error message without the "Keitaro: " prefix the error class adds."""
    return error.message.removeprefix("Keitaro: ").capitalize()
