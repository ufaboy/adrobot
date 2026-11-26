from fastapi import APIRouter

from app.api.deps import ReferenceServiceDep
from app.schemas.reference import ReferenceData

router = APIRouter(prefix="/reference", tags=["reference"])


@router.get("")
async def get_reference(reference: ReferenceServiceDep) -> ReferenceData:
    """Domains, groups, traffic sources, countries and defaults for the campaign creator."""
    return await reference.creator_reference()
