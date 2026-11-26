"""Pydantic models of the Keitaro Admin API v1 payloads we use.

Response models ignore unknown fields: Keitaro returns many attributes we do not need.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _KeitaroModel(BaseModel):
    model_config = ConfigDict(extra="ignore", validate_by_name=True, validate_by_alias=True)


# --- Reference data ---------------------------------------------------------------


class KeitaroOffer(_KeitaroModel):
    id: int
    name: str
    state: str
    country: list[str] = []


class KeitaroDomain(_KeitaroModel):
    id: int
    name: str
    state: str = "active"


class KeitaroGroup(_KeitaroModel):
    id: int
    name: str


class KeitaroTrafficSource(_KeitaroModel):
    id: int
    name: str
    state: str = "active"


# --- Campaigns and streams --------------------------------------------------------


class KeitaroCampaign(_KeitaroModel):
    id: int
    alias: str
    name: str
    state: str
    group_id: int | None = None
    domain_id: int | None = None
    traffic_source_id: int | None = None


class KeitaroStreamFilter(_KeitaroModel):
    name: str
    mode: Literal["accept", "reject"]
    payload: list[str]


class KeitaroStreamOffer(_KeitaroModel):
    offer_id: int
    share: int
    state: str = "active"


class KeitaroStream(_KeitaroModel):
    id: int
    campaign_id: int
    name: str
    type: str
    position: int
    state: str
    # `schema` shadows a BaseModel attribute, hence the alias.
    schema_: str | None = Field(default=None, alias="schema")
    action_type: str | None = None
    action_payload: str | None = None
    filters: list[KeitaroStreamFilter] = []
    offers: list[KeitaroStreamOffer] = []


class CampaignCreatePayload(_KeitaroModel):
    name: str
    # Set by us so a campaign whose create response was lost can be found again.
    alias: str | None = None
    type: Literal["position", "weight"] = "position"
    group_id: int
    domain_id: int
    traffic_source_id: int
    cost_type: str = "CPC"
    cost_value: float = 0
    cost_currency: str = "USD"
    state: str = "active"


class StreamCreatePayload(_KeitaroModel):
    campaign_id: int
    name: str
    type: Literal["regular", "forced", "default"] = "regular"
    position: int
    weight: int = 100
    state: str = "active"
    schema_: Literal["redirect", "landings", "action"] = Field(alias="schema")
    action_type: str = "http"
    action_payload: str | None = None
    filter_or: bool = False
    filters: list[KeitaroStreamFilter] = []
    offers: list[KeitaroStreamOffer] = []
    collect_clicks: bool = True

    def to_json(self) -> dict[str, object]:
        return self.model_dump(by_alias=True, exclude_none=True)
