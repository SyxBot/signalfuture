import asyncio
import time


class RateLimiter:
    """Async token-bucket rate limiter."""

    def __init__(self, rate: float = 2.0, burst: int = 5):
        self._rate = rate
        self._burst = burst
        self._tokens = float(burst)
        self._last = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, timeout: float = 30.0) -> None:
        deadline = time.monotonic() + timeout
        while True:
            async with self._lock:
                now = time.monotonic()
                elapsed = now - self._last
                self._tokens = min(self._burst, self._tokens + elapsed * self._rate)
                self._last = now
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                wait = (1.0 - self._tokens) / self._rate

            if time.monotonic() + wait > deadline:
                raise TimeoutError("Rate limiter timeout exceeded")
            await asyncio.sleep(min(wait, 0.05))

    def throttle(self, factor: float = 0.5) -> None:
        """Temporarily reduce rate (e.g. on 429 response)."""
        self._rate = max(0.1, self._rate * factor)

    def reset_rate(self, rate: float) -> None:
        self._rate = rate
