from datetime import datetime

from pydantic import BaseModel, Field


class CampaignSummary(BaseModel):
    id: int = Field(description="Keitaro campaign id")
    name: str
    alias: str
    state: str


class StreamOfferOut(BaseModel):
    offer_id: int
    name: str | None = Field(description="From the local offer catalog; null if unknown")
    state: str = Field(description="active | removed")
    share: int
    pinned: bool
    is_new: bool = Field(description="Added locally and never pushed to Keitaro")
    is_dirty: bool
    published_share: int | None


class StreamOut(BaseModel):
    id: int = Field(description="Keitaro stream id")
    name: str
    type: str
    position: int
    editable: bool = Field(description="False for streams without offers (shown read-only)")
    dirty: bool = Field(description="Has changes not pushed to Keitaro")
    total_share: int
    push_blocker: str | None = Field(description="Why Push is not possible, if it is not")
    offers: list[StreamOfferOut]


class CampaignEditorOut(BaseModel):
    id: int = Field(description="Keitaro campaign id")
    name: str
    alias: str
    fetched_at: datetime | None
    streams: list[StreamOut]


class AddOfferRequest(BaseModel):
    offer_id: int = Field(gt=0)


class SetShareRequest(BaseModel):
    share: int = Field(ge=0, le=100)
