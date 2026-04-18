import asyncio
import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from api.deps import get_feed_service

router = APIRouter()


@router.get("/stream")
async def sse_stream(request: Request):
    feed_svc = get_feed_service(request)
    q: asyncio.Queue = asyncio.Queue(maxsize=10)
    feed_svc.subscribers.append(q)

    async def generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    tokens = await asyncio.wait_for(q.get(), timeout=30)
                    payload = json.dumps([t.model_dump(mode="json") for t in tokens])
                    yield f"data: {payload}\n\n"
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            try:
                feed_svc.subscribers.remove(q)
            except ValueError:
                pass

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
