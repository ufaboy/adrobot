from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OfferState(StrEnum):
    ACTIVE = "active"
    REMOVED = "removed"


class Stream(Base):
    """Local snapshot of a Keitaro stream (flow)."""

    __tablename__ = "streams"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"))
    keitaro_id: Mapped[int] = mapped_column(unique=True)
    name: Mapped[str] = mapped_column(String(255))
    type: Mapped[str] = mapped_column(String(32))
    position: Mapped[int]
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    offers: Mapped[list["StreamOffer"]] = relationship(
        back_populates="stream",
        cascade="all, delete-orphan",
        order_by="StreamOffer.position",
    )

    @property
    def is_offer_stream(self) -> bool:
        """Streams without offers (e.g. a plain redirect) are shown read-only."""
        return bool(self.offers)

    @property
    def is_dirty(self) -> bool:
        return any(offer.is_dirty for offer in self.offers)


class StreamOffer(Base):
    """An offer in a stream: the editable draft plus the last state published to Keitaro.

    `published_*` columns hold the state last synced with Keitaro. They are NULL for an
    offer added locally and never pushed. A stream is dirty when any draft differs from it.
    """

    __tablename__ = "stream_offers"

    id: Mapped[int] = mapped_column(primary_key=True)
    stream_id: Mapped[int] = mapped_column(ForeignKey("streams.id", ondelete="CASCADE"))
    # Keitaro offer id. No FK: the stream may reference offers missing from the catalog.
    offer_id: Mapped[int]
    position: Mapped[int]

    state: Mapped[str] = mapped_column(String(16))
    share: Mapped[int]
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)

    published_state: Mapped[str | None] = mapped_column(String(16))
    published_share: Mapped[int | None]
    published_pinned: Mapped[bool | None] = mapped_column(Boolean)

    stream: Mapped[Stream] = relationship(back_populates="offers")

    __table_args__ = (UniqueConstraint("stream_id", "offer_id"),)

    @property
    def is_new(self) -> bool:
        return self.published_state is None

    @property
    def is_dirty(self) -> bool:
        return (
            self.is_new
            or self.state != self.published_state
            or self.share != self.published_share
            or self.pinned != self.published_pinned
        )

    def mark_published(self) -> None:
        self.published_state = self.state
        self.published_share = self.share
        self.published_pinned = self.pinned
