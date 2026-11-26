from pydantic import BaseModel, ConfigDict


class OfferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    state: str
    countries: list[str]


class OfferSyncResult(BaseModel):
    count: int
