from datetime import timedelta
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.integrations.keitaro import KeitaroClient
from app.services.campaigns import CampaignIdempotency, CampaignService
from app.services.editor import EditorService
from app.services.offers import OfferService
from app.services.reference import ReferenceCache, ReferenceService

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_keitaro_client(request: Request) -> KeitaroClient:
    client: KeitaroClient = request.app.state.keitaro
    return client


def get_reference_cache(request: Request) -> ReferenceCache:
    cache: ReferenceCache = request.app.state.reference_cache
    return cache


def get_campaign_idempotency(request: Request) -> CampaignIdempotency:
    store: CampaignIdempotency = request.app.state.campaign_idempotency
    return store


KeitaroDep = Annotated[KeitaroClient, Depends(get_keitaro_client)]


def get_offer_service(
    session: SessionDep, keitaro: KeitaroDep, settings: SettingsDep
) -> OfferService:
    return OfferService(session, keitaro, timedelta(minutes=settings.offers_cache_ttl_minutes))


def get_reference_service(
    keitaro: KeitaroDep,
    cache: Annotated[ReferenceCache, Depends(get_reference_cache)],
    settings: SettingsDep,
) -> ReferenceService:
    return ReferenceService(keitaro, cache, settings)


OfferServiceDep = Annotated[OfferService, Depends(get_offer_service)]
ReferenceServiceDep = Annotated[ReferenceService, Depends(get_reference_service)]


def get_campaign_service(
    session: SessionDep,
    keitaro: KeitaroDep,
    offers: OfferServiceDep,
    reference: ReferenceServiceDep,
    settings: SettingsDep,
    idempotency: Annotated[CampaignIdempotency, Depends(get_campaign_idempotency)],
) -> CampaignService:
    return CampaignService(session, keitaro, offers, reference, settings.google_url, idempotency)


CampaignServiceDep = Annotated[CampaignService, Depends(get_campaign_service)]


def get_editor_service(
    session: SessionDep, keitaro: KeitaroDep, offers: OfferServiceDep
) -> EditorService:
    return EditorService(session, keitaro, offers)


EditorServiceDep = Annotated[EditorService, Depends(get_editor_service)]
