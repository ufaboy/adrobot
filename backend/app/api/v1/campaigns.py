from typing import Annotated

from fastapi import APIRouter, Header, status

from app.api.deps import CampaignServiceDep, EditorServiceDep
from app.schemas.campaigns import CampaignCreate, CampaignCreated
from app.schemas.editor import CampaignEditorOut, CampaignSummary

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get("")
async def list_campaigns(editor: EditorServiceDep) -> list[CampaignSummary]:
    """Campaigns from Keitaro, newest first."""
    return await editor.list_campaigns()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_campaign(
    data: CampaignCreate,
    campaigns: CampaignServiceDep,
    idempotency_key: Annotated[str | None, Header(min_length=1, max_length=200)] = None,
) -> CampaignCreated:
    """Create a Keitaro campaign with a geo-redirect stream and an offer stream.

    Send an `Idempotency-Key` header to make retries safe: a repeated key returns the
    first result (409 while it is still running, 422 if reused with a different body).
    """
    return await campaigns.create(data, idempotency_key)


@router.get("/{campaign_id}")
async def get_campaign(campaign_id: int, editor: EditorServiceDep) -> CampaignEditorOut:
    """The local editor snapshot of a campaign (fetched from Keitaro on first open)."""
    return await editor.get_campaign(campaign_id)


@router.post("/{campaign_id}/fetch")
async def fetch_campaign(campaign_id: int, editor: EditorServiceDep) -> CampaignEditorOut:
    """Re-read streams from Keitaro. Unpublished changes are discarded."""
    return await editor.fetch_campaign(campaign_id)
