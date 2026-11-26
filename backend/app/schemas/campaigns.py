from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, field_validator

from app.services.countries import is_country_code

CampaignName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
]


class CampaignCreate(BaseModel):
    name: CampaignName
    geo: list[str] = Field(min_length=1, description="ISO 3166-1 alpha-2 country codes")
    offer_id: int = Field(gt=0)
    domain_id: int = Field(gt=0)
    group_id: int = Field(gt=0)
    traffic_source_id: int = Field(gt=0)

    @field_validator("geo")
    @classmethod
    def normalize_geo(cls, value: list[str]) -> list[str]:
        codes: list[str] = []
        for raw in value:
            code = raw.strip().upper()
            if not is_country_code(code):
                raise ValueError(f"unknown country code: {raw!r}")
            if code not in codes:
                codes.append(code)
        return codes


class CampaignCreated(BaseModel):
    id: int = Field(description="Keitaro campaign id")
    name: str
    alias: str
    geo: list[str]
    offer_id: int
    stream_ids: list[int]
