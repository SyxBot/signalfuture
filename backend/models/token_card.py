from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class SmartMoneySignal(BaseModel):
    wallet_address: str
    win_rate: float
    pnl_usd: float
    avg_hold_hours: float
    bought_at: datetime


class TokenCard(BaseModel):
    # Identity
    mint: str
    symbol: str
    name: str
    logo_uri: Optional[str] = None
    source: str
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Market data
    price_usd: float = 0.0
    market_cap_usd: Optional[float] = None
    liquidity_usd: float = 0.0
    volume_1h_usd: float = 0.0
    volume_24h_usd: float = 0.0
    real_volume_24h_usd: float = 0.0
    buy_count_1h: int = 0
    sell_count_1h: int = 0
    buy_sell_ratio: float = 0.0

    # Token attributes
    age_seconds: int = 0
    holder_count: int = 0
    top10_holder_pct: float = 0.0

    # Security
    contract_renounced: bool = False
    lp_burned: bool = False
    is_honeypot: bool = False
    buy_tax: float = 0.0
    sell_tax: float = 0.0

    # Smart money
    smart_money_buyers: list[SmartMoneySignal] = Field(default_factory=list)
    smart_money_count: int = 0
    smart_buy_24h: int = 0
    smart_sell_24h: int = 0
