import asyncio
import logging
from typing import List

from gmgn import endpoints as EP
from gmgn.client import GMGNClient
from models.token_card import TokenCard
from services.normalizer import apply_security_overlay, normalize_token

log = logging.getLogger(__name__)


class TokenFeedService:
    def __init__(self, client: GMGNClient, cache, poll_interval: int = 30):
        self._client = client
        self._cache = cache
        self._poll_interval = poll_interval
        self.subscribers: list[asyncio.Queue] = []

    async def run_forever(self) -> None:
        while True:
            try:
                await self._poll_all_feeds()
            except Exception as exc:
                log.error("Poll cycle error: %s", exc)
            await asyncio.sleep(self._poll_interval)

    async def handle_ws_message(self, msg: dict) -> None:
        """Called by the WebSocket client on each incoming message."""
        channel = msg.get("channel", "")
        data = msg.get("data", {})
        if not data:
            return

        if channel in ("token_launches", "new_pools"):
            tokens_raw = data if isinstance(data, list) else [data]
            cards = []
            for raw in tokens_raw:
                try:
                    card = normalize_token(raw, source="ws_" + channel)
                    self._cache.upsert_token(card)
                    cards.append(card)
                except Exception as exc:
                    log.warning("WS normalize error: %s", exc)
            if cards:
                await self._notify_subscribers(cards)

    async def _poll_all_feeds(self) -> None:
        trending, new_tokens, bonded = await asyncio.gather(
            self._fetch_rank("1h"),
            self._fetch_new(),
            self._fetch_almost_bonded(),
            return_exceptions=True,
        )

        merged = self._merge_and_dedupe(
            trending if isinstance(trending, list) else [],
            new_tokens if isinstance(new_tokens, list) else [],
            bonded if isinstance(bonded, list) else [],
        )

        enriched: List[TokenCard] = []
        for card in merged:
            sec = self._cache.get_security(card.mint)
            if sec is None:
                try:
                    sec = await self._fetch_security(card.mint)
                    self._cache.set_security(card.mint, sec, ttl=300)
                except Exception as exc:
                    log.debug("Security fetch failed for %s: %s", card.mint, exc)
                    sec = {}
            if sec:
                card = apply_security_overlay(card, sec)
            self._cache.upsert_token(card)
            enriched.append(card)

        if enriched:
            log.info("Poll cycle: %d tokens upserted", len(enriched))
            await self._notify_subscribers(enriched)

    async def _fetch_rank(self, time_period: str) -> List[TokenCard]:
        path = EP.RANK_SWAPS.format(time_period=time_period)
        data = await self._client.get(path, params=EP.RANK_PARAMS)
        return [normalize_token(t, f"rank_{time_period}")
                for t in data.get("data", {}).get("rank", [])]

    async def _fetch_new(self) -> List[TokenCard]:
        data = await self._client.get(EP.NEW_TOKENS)
        raw_data = data.get("data", {})
        if isinstance(raw_data, list):
            items = raw_data
        else:
            items = raw_data.get("tokens", [])
        return [normalize_token(t, "new") for t in items]

    async def _fetch_almost_bonded(self) -> List[TokenCard]:
        data = await self._client.get(EP.ALMOST_BONDED)
        tokens_raw = data.get("data", {})
        if isinstance(tokens_raw, list):
            items = tokens_raw
        else:
            items = tokens_raw.get("tokens", [])
        return [normalize_token(t, "almost_bonded") for t in items]

    async def _fetch_security(self, mint: str) -> dict:
        data = await self._client.get(EP.TOKEN_SECURITY, params={**EP.CHAIN_SOL, "address": mint})
        return data.get("data", {})

    def _merge_and_dedupe(self, *feeds) -> List[TokenCard]:
        seen: set[str] = set()
        result: List[TokenCard] = []
        for feed in feeds:
            for card in feed:
                if card.mint and card.mint not in seen:
                    seen.add(card.mint)
                    result.append(card)
        return result

    async def _notify_subscribers(self, tokens: List[TokenCard]) -> None:
        dead = []
        for q in self.subscribers:
            try:
                q.put_nowait(tokens)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            self.subscribers.remove(q)
