from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import OfferServiceDep
from app.schemas.offers import OfferOut, OfferSyncResult

router = APIRouter(prefix="/offers", tags=["offers"])


@router.get("")
async def search_offers(
    offers: OfferServiceDep,
    q: Annotated[str, Query(max_length=100, description="Offer id prefix or name part")] = "",
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> list[OfferOut]:
    """Search active offers in the local catalog (synced from Keitaro when stale)."""
    found = await offers.search(q, limit=limit)
    return [OfferOut.model_validate(o) for o in found]


@router.post("/refresh")
async def refresh_offers(offers: OfferServiceDep) -> OfferSyncResult:
    """Force a reload of the offer catalog from Keitaro."""
    return OfferSyncResult(count=await offers.sync())
