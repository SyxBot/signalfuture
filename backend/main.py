import asyncio
import logging
import logging.config
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import filters, smart_money, stream, tokens
from cache.sqlite_cache import SQLiteCache
from core.config import settings
from core.rate_limiter import RateLimiter
from gmgn.client import GMGNClient
from gmgn.ws_client import GMGNWebSocket
from services.filter_engine import FilterEngine
from services.smart_money_tracker import SmartMoneyTracker
from services.token_feed import TokenFeedService

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    limiter = RateLimiter(rate=settings.RATE_REQ_PER_SEC, burst=settings.RATE_BURST)
    client = GMGNClient(limiter)
    cache = SQLiteCache(settings.SQLITE_PATH)

    feed_svc = TokenFeedService(client, cache, poll_interval=settings.POLL_INTERVAL_SECONDS)
    sm_tracker = SmartMoneyTracker(client, cache)
    ws_client = GMGNWebSocket(settings.GMGN_ACCESS_TOKEN, feed_svc.handle_ws_message)

    app.state.cache = cache
    app.state.filter_engine = FilterEngine()
    app.state.feed_service = feed_svc

    tasks = [
        asyncio.create_task(feed_svc.run_forever(), name="token_feed"),
        asyncio.create_task(sm_tracker.run_forever(), name="smart_money"),
    ]
    if settings.GMGN_ACCESS_TOKEN:
        tasks.append(asyncio.create_task(ws_client.run_forever(), name="ws_client"))
    else:
        log.warning("GMGN_ACCESS_TOKEN not set — WebSocket disabled, polling only")

    log.info("zookAgent started (poll_interval=%ds)", settings.POLL_INTERVAL_SECONDS)
    yield

    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    cache.close()
    await client.close()
    log.info("zookAgent shutdown complete")


app = FastAPI(title="zookAgent — GMGN Solana Token Filter", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(tokens.router, prefix="/api")
app.include_router(filters.router, prefix="/api")
app.include_router(smart_money.router, prefix="/api")
app.include_router(stream.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}
