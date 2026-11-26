from fastapi import APIRouter

from app.api.deps import EditorServiceDep
from app.schemas.editor import AddOfferRequest, SetShareRequest, StreamOut

router = APIRouter(prefix="/streams", tags=["streams"])

# All edits change the local draft only and return the recalculated stream.
# `stream_id` is the Keitaro stream id.


@router.post("/{stream_id}/offers")
async def add_offer(stream_id: int, data: AddOfferRequest, editor: EditorServiceDep) -> StreamOut:
    return await editor.add_offer(stream_id, data.offer_id)


@router.post("/{stream_id}/offers/{offer_id}/remove")
async def remove_offer(stream_id: int, offer_id: int, editor: EditorServiceDep) -> StreamOut:
    return await editor.remove_offer(stream_id, offer_id)


@router.post("/{stream_id}/offers/{offer_id}/bring-back")
async def bring_back_offer(stream_id: int, offer_id: int, editor: EditorServiceDep) -> StreamOut:
    return await editor.bring_back_offer(stream_id, offer_id)


@router.put("/{stream_id}/offers/{offer_id}/share")
async def set_share(
    stream_id: int, offer_id: int, data: SetShareRequest, editor: EditorServiceDep
) -> StreamOut:
    """Set a share manually. The share becomes pinned."""
    return await editor.set_share(stream_id, offer_id, data.share)


@router.post("/{stream_id}/offers/{offer_id}/unpin")
async def unpin(stream_id: int, offer_id: int, editor: EditorServiceDep) -> StreamOut:
    return await editor.unpin(stream_id, offer_id)


@router.post("/{stream_id}/push")
async def push(stream_id: int, editor: EditorServiceDep) -> StreamOut:
    """Publish the stream's active offers and shares to Keitaro."""
    return await editor.push(stream_id)


@router.post("/{stream_id}/cancel")
async def cancel(stream_id: int, editor: EditorServiceDep) -> StreamOut:
    """Revert all unpublished changes of the stream."""
    return await editor.cancel(stream_id)
