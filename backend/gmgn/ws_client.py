import asyncio
import json
import logging
from collections.abc import Awaitable, Callable

import websockets

log = logging.getLogger(__name__)

MessageCallback = Callable[[dict], Awaitable[None]]


class GMGNWebSocket:
    """Connects to the official GMGN WebSocket and fans messages out to a callback."""

    def __init__(self, access_token: str, on_message: MessageCallback):
        self._token = access_token
        self._on_message = on_message

    async def run_forever(self) -> None:
        uri = f"wss://gmgn.ai/ws?access_token={self._token}"
        while True:
            try:
                async with websockets.connect(uri, ping_interval=30, ping_timeout=10) as ws:
                    log.info("GMGN WebSocket connected")
                    await self._subscribe(ws)
                    async for raw in ws:
                        try:
                            msg = json.loads(raw)
                            await self._on_message(msg)
                        except Exception as exc:
                            log.warning("WS message handling error: %s", exc)
            except Exception as exc:
                log.error("WS disconnected (%s) — reconnecting in 5 s", exc)
                await asyncio.sleep(5)

    async def _subscribe(self, ws) -> None:
        subs = [
            {"op": "subscribe", "channel": "token_launches", "chain": "sol"},
            {"op": "subscribe", "channel": "new_pools", "chain": "sol"},
        ]
        for sub in subs:
            await ws.send(json.dumps(sub))
