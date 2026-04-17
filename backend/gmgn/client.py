import asyncio
import logging

import httpx

from core.config import settings
from core.rate_limiter import RateLimiter
from .exceptions import AuthError, GMGNError, RateLimitError

log = logging.getLogger(__name__)

BASE_URL = "https://gmgn.ai"


class GMGNClient:
    def __init__(self, limiter: RateLimiter):
        self._limiter = limiter
        self._http = httpx.AsyncClient(
            base_url=BASE_URL,
            headers={
                "Authorization": f"Bearer {settings.GMGN_ACCESS_TOKEN}",
                "Accept": "application/json",
            },
            timeout=12.0,
        )

    async def get(self, path: str, params: dict | None = None, retries: int = 3) -> dict:
        await self._limiter.acquire()
        last_exc: Exception | None = None
        for attempt in range(retries):
            try:
                resp = await self._http.get(path, params=params)
            except httpx.RequestError as exc:
                last_exc = exc
                wait = 2 ** attempt
                log.warning("Request error on %s (attempt %d): %s — retrying in %ds", path, attempt, exc, wait)
                await asyncio.sleep(wait)
                continue

            if resp.status_code == 401:
                raise AuthError("Invalid or missing GMGN_ACCESS_TOKEN")

            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 30))
                log.warning("429 on %s — backing off %ds", path, retry_after)
                self._limiter.throttle(0.5)
                await asyncio.sleep(retry_after)
                raise RateLimitError(f"Rate limited on {path}")

            resp.raise_for_status()

            data = resp.json()
            if data.get("code", 0) != 0:
                raise GMGNError(f"GMGN error on {path}: {data.get('msg', 'unknown')}")

            return data

        raise last_exc or GMGNError(f"All retries exhausted for {path}")

    async def close(self) -> None:
        await self._http.aclose()
