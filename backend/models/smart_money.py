from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class RecentTrade(BaseModel):
    mint: str
    symbol: str
    side: str
    amount_usd: float
    pnl_usd: Optional[float] = None
    timestamp: datetime


class SmartMoneyWallet(BaseModel):
    address: str
    win_rate: float = 0.0
    realized_pnl_usd: float = 0.0
    unrealized_pnl_usd: float = 0.0
    total_pnl_usd: float = 0.0
    avg_hold_hours: float = 0.0
    trade_count_30d: int = 0
    wallet_type: str = "unknown"
    last_active: Optional[datetime] = None
    recent_trades: list[RecentTrade] = Field(default_factory=list)
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
