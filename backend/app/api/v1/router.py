from fastapi import APIRouter

from app.api.v1 import campaigns, offers, reference, streams

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(reference.router)
api_router.include_router(offers.router)
api_router.include_router(campaigns.router)
api_router.include_router(streams.router)
