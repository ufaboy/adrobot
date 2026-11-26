from datetime import UTC, datetime

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError, ValidationFailedError
from app.integrations.keitaro import KeitaroClient, KeitaroRejectedError
from app.models import Campaign, OfferState, Stream, StreamOffer
from app.repositories.streams import EditorRepository
from app.schemas.editor import CampaignEditorOut, CampaignSummary, StreamOfferOut, StreamOut
from app.services import stream_rules
from app.services.offers import OfferService
from app.services.weights import WeightError


class EditorService:
    """Campaign editor: local snapshot of Keitaro streams, drafts, push and cancel."""

    def __init__(self, session: AsyncSession, keitaro: KeitaroClient, offers: OfferService) -> None:
        self._session = session
        self._keitaro = keitaro
        self._offers = offers
        self._repo = EditorRepository(session)

    # --- Campaigns ----------------------------------------------------------------

    async def list_campaigns(self) -> list[CampaignSummary]:
        campaigns = await self._keitaro.list_campaigns()
        return [
            CampaignSummary(id=c.id, name=c.name, alias=c.alias, state=c.state)
            for c in sorted(campaigns, key=lambda c: c.id, reverse=True)
        ]

    async def get_campaign(self, keitaro_id: int) -> CampaignEditorOut:
        """The local snapshot; fetched from Keitaro on first open."""
        campaign = await self._repo.get_campaign(keitaro_id)
        if campaign is None or campaign.fetched_at is None:
            return await self.fetch_campaign(keitaro_id)
        return await self._campaign_out(campaign)

    async def fetch_campaign(self, keitaro_id: int) -> CampaignEditorOut:
        """Refresh the snapshot from Keitaro, discarding unpublished changes."""
        remote_campaign = await self._keitaro.get_campaign(keitaro_id)
        remote_streams = await self._keitaro.list_streams(keitaro_id)
        for remote in remote_streams:
            duplicates = stream_rules.duplicate_offer_ids(remote.offers)
            if duplicates:
                listed = ", ".join(str(i) for i in duplicates)
                raise ValidationFailedError(
                    f"Stream {remote.id} in Keitaro lists offer {listed} more than once; "
                    "fix the stream in Keitaro and fetch again"
                )
        now = datetime.now(UTC)

        campaign = await self._repo.get_campaign(keitaro_id)
        if campaign is None:
            campaign = Campaign(keitaro_id=keitaro_id, streams=[])
            self._session.add(campaign)
        campaign.name = remote_campaign.name
        campaign.alias = remote_campaign.alias
        campaign.fetched_at = now

        existing = {s.keitaro_id: s for s in campaign.streams}
        for remote in remote_streams:
            stream = existing.pop(remote.id, None)
            if stream is None:
                stream = Stream(keitaro_id=remote.id, offers=[])
                campaign.streams.append(stream)
            stream.name = remote.name
            stream.type = remote.type
            stream.position = remote.position
            stream.fetched_at = now
            stream_rules.apply_fetched_offers(stream, remote.offers)
        for gone in existing.values():
            campaign.streams.remove(gone)

        await self._session.commit()
        return await self._reload_campaign(keitaro_id)

    # --- Stream edits ---------------------------------------------------------------

    async def add_offer(self, stream_id: int, offer_id: int) -> StreamOut:
        stream = await self._editable_stream(stream_id)
        row = _find(stream, offer_id)
        if row is not None:
            if row.state == OfferState.REMOVED:
                raise ConflictError(
                    f"Offer {offer_id} was removed from this stream; bring it back instead"
                )
            raise ConflictError(f"Offer {offer_id} is already in this stream")

        await self._require_active_offer(offer_id)

        position = max((o.position for o in stream.offers), default=-1) + 1
        stream.offers.append(
            StreamOffer(
                offer_id=offer_id,
                position=position,
                state=OfferState.ACTIVE,
                share=0,
                pinned=False,
            )
        )
        return await self._rebalance_and_save(stream)

    async def remove_offer(self, stream_id: int, offer_id: int) -> StreamOut:
        stream = await self._editable_stream(stream_id)
        row = self._require_offer(stream, offer_id)
        if row.state == OfferState.REMOVED:
            raise ConflictError(f"Offer {offer_id} is already removed")
        row.state = OfferState.REMOVED
        row.pinned = False
        return await self._rebalance_and_save(stream)

    async def bring_back_offer(self, stream_id: int, offer_id: int) -> StreamOut:
        stream = await self._editable_stream(stream_id)
        row = self._require_offer(stream, offer_id)
        if row.state == OfferState.ACTIVE:
            raise ConflictError(f"Offer {offer_id} is already active")
        await self._require_active_offer(offer_id)
        row.state = OfferState.ACTIVE
        return await self._rebalance_and_save(stream)

    async def set_share(self, stream_id: int, offer_id: int, share: int) -> StreamOut:
        """Set a share manually; it becomes pinned."""
        stream = await self._editable_stream(stream_id)
        row = self._require_offer(stream, offer_id)
        if row.state != OfferState.ACTIVE:
            raise ConflictError(f"Offer {offer_id} is removed; bring it back first")
        row.share = share
        row.pinned = True
        return await self._rebalance_and_save(stream)

    async def unpin(self, stream_id: int, offer_id: int) -> StreamOut:
        stream = await self._editable_stream(stream_id)
        row = self._require_offer(stream, offer_id)
        row.pinned = False
        return await self._rebalance_and_save(stream)

    async def push(self, stream_id: int) -> StreamOut:
        """Publish the stream's draft to Keitaro.

        The stream is read from Keitaro first, so a change made there since the last fetch
        is not overwritten. If Keitaro already holds the draft (an earlier push whose
        response was lost), the draft is recorded as published without sending it again.
        """
        stream = await self._editable_stream(stream_id)
        if not stream.is_dirty:
            raise ConflictError("There are no unpublished changes")
        blocker = stream_rules.stream_push_blocker(stream)
        if blocker is not None:
            raise ValidationFailedError(blocker)

        try:
            remote_stream = await self._keitaro.get_stream(stream_id)
        except KeitaroRejectedError as exc:
            if exc.upstream_status != status.HTTP_404_NOT_FOUND:
                raise
            raise ConflictError(
                f"Stream {stream_id} was deleted in Keitaro. Fetch streams from KT"
            ) from exc
        remote = stream_rules.remote_shares(remote_stream.offers)
        if remote == stream_rules.published_shares(stream):
            await self._keitaro.update_stream_offers(
                stream.keitaro_id, stream_rules.payload_offers(stream)
            )
        elif remote != stream_rules.draft_shares(stream):
            raise ConflictError(
                f"Stream {stream_id} was changed in Keitaro since the last fetch. "
                "Fetch streams from KT to see the changes; this discards your unpublished ones"
            )
        stream_rules.mark_pushed(stream)
        await self._session.commit()
        return await self._reload_stream(stream_id)

    async def cancel(self, stream_id: int) -> StreamOut:
        stream = await self._editable_stream(stream_id)
        stream_rules.cancel_changes(stream)
        await self._session.commit()
        return await self._reload_stream(stream_id)

    # --- Helpers ----------------------------------------------------------------------

    async def _editable_stream(self, stream_id: int) -> Stream:
        """The stream to change, locked until commit (409 if another change holds it)."""
        stream = await self._repo.get_stream(stream_id, lock=True)
        if stream is None:
            raise NotFoundError(f"Stream {stream_id} is not in the local snapshot; fetch it")
        if not stream.is_offer_stream:
            raise ValidationFailedError(f"Stream {stream_id} has no offers and is read-only")
        return stream

    async def _require_active_offer(self, offer_id: int) -> None:
        """Only offers active in the catalog may join a stream's active offers."""
        offer = await self._offers.get_fresh(offer_id)
        if offer is None:
            raise ValidationFailedError(f"Offer {offer_id} does not exist")
        if offer.state != "active":
            raise ValidationFailedError(f"Offer {offer_id} is not active")

    @staticmethod
    def _require_offer(stream: Stream, offer_id: int) -> StreamOffer:
        row = _find(stream, offer_id)
        if row is None:
            raise NotFoundError(f"Offer {offer_id} is not in stream {stream.keitaro_id}")
        return row

    async def _rebalance_and_save(self, stream: Stream) -> StreamOut:
        try:
            stream_rules.rebalance_stream(stream)
        except WeightError as exc:
            await self._session.rollback()
            raise ValidationFailedError(str(exc)) from exc
        await self._session.commit()
        return await self._reload_stream(stream.keitaro_id)

    async def _reload_stream(self, stream_id: int) -> StreamOut:
        stream = await self._repo.get_stream(stream_id)
        assert stream is not None
        names = await self._repo.offer_names({o.offer_id for o in stream.offers})
        return _stream_out(stream, names)

    async def _reload_campaign(self, keitaro_id: int) -> CampaignEditorOut:
        campaign = await self._repo.get_campaign(keitaro_id)
        assert campaign is not None
        return await self._campaign_out(campaign)

    async def _campaign_out(self, campaign: Campaign) -> CampaignEditorOut:
        ids = {o.offer_id for s in campaign.streams for o in s.offers}
        names = await self._repo.offer_names(ids)
        return CampaignEditorOut(
            id=campaign.keitaro_id,
            name=campaign.name,
            alias=campaign.alias,
            fetched_at=campaign.fetched_at,
            streams=[
                _stream_out(s, names) for s in sorted(campaign.streams, key=lambda s: s.position)
            ],
        )


def _find(stream: Stream, offer_id: int) -> StreamOffer | None:
    return next((o for o in stream.offers if o.offer_id == offer_id), None)


def _stream_out(stream: Stream, names: dict[int, str]) -> StreamOut:
    offers = stream_rules.ordered(stream)
    editable = stream.is_offer_stream
    return StreamOut(
        id=stream.keitaro_id,
        name=stream.name,
        type=stream.type,
        position=stream.position,
        editable=editable,
        dirty=stream.is_dirty,
        total_share=sum(o.share for o in offers if o.state == OfferState.ACTIVE),
        push_blocker=stream_rules.stream_push_blocker(stream) if editable else None,
        offers=[
            StreamOfferOut(
                offer_id=o.offer_id,
                name=names.get(o.offer_id),
                state=o.state,
                share=o.share,
                pinned=o.pinned,
                is_new=o.is_new,
                is_dirty=o.is_dirty,
                published_share=o.published_share,
            )
            for o in offers
        ],
    )
