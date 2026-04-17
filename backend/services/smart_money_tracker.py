import asyncio
import logging
from datetime import datetime, timezone

from gmgn import endpoints as EP
from gmgn.client import GMGNClient
from models.token_card import SmartMoneySignal
from services.normalizer import normalize_wallet

log = logging.getLogger(__name__)

SWEEP_INTERVAL = 60  # seconds
MAX_WALLETS_PER_CYCLE = 15


class SmartMoneyTracker:
    def __init__(self, client: GMGNClient, cache):
        self._client = client
        self._cache = cache

    async def run_forever(self) -> None:
        while True:
            try:
                await self._sweep()
            except Exception as exc:
                log.error("Smart money sweep error: %s", exc)
            await asyncio.sleep(SWEEP_INTERVAL)

    async def _sweep(self) -> None:
        # Pull top trader addresses from recent token-info calls in cache
        mints = self._cache.get_recent_mints(limit=20)
        wallet_to_mints: dict[str, list[str]] = {}

        for mint in mints:
            try:
                data = await self._client.get(
                    EP.TOKEN_INFO, params={**EP.CHAIN_SOL, "address": mint}
                )
                top_traders = data.get("data", {}).get("top_traders", [])
                for trader in top_traders:
                    addr = trader.get("address")
                    if addr:
                        wallet_to_mints.setdefault(addr, []).append(mint)
            except Exception as exc:
                log.debug("Token info fetch failed for %s: %s", mint, exc)

        # Enrich wallets (cache-first, cap at MAX_WALLETS_PER_CYCLE)
        addresses = list(wallet_to_mints.keys())[:MAX_WALLETS_PER_CYCLE]
        for addr in addresses:
            wallet = self._cache.get_wallet(addr)
            if wallet is None:
                try:
                    raw = await self._client.get(
                        EP.WALLET_STATS, params={**EP.CHAIN_SOL, "address": addr}
                    )
                    wallet = normalize_wallet(addr, raw.get("data", {}))
                    self._cache.set_wallet(wallet, ttl=600)
                    await asyncio.sleep(1)  # 1 req/s for wallet enrichment
                except Exception as exc:
                    log.debug("Wallet fetch failed for %s: %s", addr, exc)
                    continue

            # Attach smart money signals to relevant token cards
            for mint in wallet_to_mints.get(addr, []):
                sig = SmartMoneySignal(
                    wallet_address=addr,
                    win_rate=wallet.win_rate,
                    pnl_usd=wallet.total_pnl_usd,
                    avg_hold_hours=wallet.avg_hold_hours,
                    bought_at=datetime.now(timezone.utc),
                )
                self._cache.attach_smart_money(mint, sig)

        log.debug("Smart money sweep done: %d wallets processed", len(addresses))
