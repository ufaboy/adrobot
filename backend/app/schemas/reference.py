from pydantic import BaseModel


class NamedItem(BaseModel):
    id: int
    name: str


class Country(BaseModel):
    code: str
    name: str


class CreatorDefaults(BaseModel):
    domain_id: int | None
    group_id: int | None
    traffic_source_id: int | None


class ReferenceData(BaseModel):
    """Everything the campaign creator form needs, except offers (searched separately)."""

    domains: list[NamedItem]
    groups: list[NamedItem]
    traffic_sources: list[NamedItem]
    countries: list[Country]
    defaults: CreatorDefaults
