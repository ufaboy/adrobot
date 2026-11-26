from datetime import datetime

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# State of an offer that has disappeared from the Keitaro catalog.
OFFER_STATE_UNAVAILABLE = "unavailable"


class Offer(Base):
    """Local mirror of the Keitaro offer catalog (read-only in Keitaro)."""

    __tablename__ = "offers"

    # Keitaro offer id; not generated locally.
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(String(500))
    state: Mapped[str] = mapped_column(String(32))
    countries: Mapped[list[str]] = mapped_column(ARRAY(String(8)), default=list)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_offers_state", "state"),)
