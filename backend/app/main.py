import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.db.session import SessionFactory
from app.integrations.keitaro import HttpKeitaroClient
from app.services.offers import OfferService
from app.services.reference import ReferenceCache

logger = logging.getLogger(__name__)

REFERENCE_CACHE_TTL_SECONDS = 600


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    keitaro = HttpKeitaroClient(
        settings.keitaro_api_url, settings.keitaro_api_key.get_secret_value()
    )
    app.state.keitaro = keitaro
    app.state.reference_cache = ReferenceCache(REFERENCE_CACHE_TTL_SECONDS)

    # Warm up the offer catalog; the app still starts if Keitaro is unavailable.
    try:
        async with SessionFactory() as session:
            ttl = timedelta(minutes=settings.offers_cache_ttl_minutes)
            await OfferService(session, keitaro, ttl).ensure_fresh()
    except Exception:
        logger.exception("Initial offer catalog sync failed")

    yield
    await keitaro.aclose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Adrobot Keitaro wrapper", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)

    app.include_router(health_router)
    app.include_router(api_router)
    return app


app = create_app()
