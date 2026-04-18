import time
from datetime import datetime, timezone
from typing import Optional

from models.smart_money import RecentTrade, SmartMoneyWallet
from models.token_card import TokenCard


def _safe_float(val) -> Optional[float]:
    try:
        return float(val) if val not in (None, "", "None") else None
    except (ValueError, TypeError):
        return None


def _safe_int(val, default: int = 0) -> int:
    try:
        return int(val) if val is not None else default
    except (ValueError, TypeError):
        return default


def normalize_token(raw: dict, source: str) -> TokenCard:
    created_ts = raw.get("pool_creation_timestamp", 0) or 0
    age_sec = max(0, int(time.time()) - int(created_ts))

    # buy/sell count field names differ across endpoints
    buy_c = _safe_int(raw.get("buy_count", raw.get("swaps", 0)))
    sell_c = _safe_int(raw.get("sell_count", 0))

    return TokenCard(
        mint=raw.get("address", raw.get("mint", "")),
        symbol=raw.get("symbol", ""),
        name=raw.get("name", raw.get("symbol", "")),
        logo_uri=raw.get("logo") or raw.get("logo_uri"),
        source=source,
        price_usd=_safe_float(raw.get("price")) or 0.0,
        market_cap_usd=_safe_float(raw.get("market_cap")),
        liquidity_usd=_safe_float(raw.get("liquidity")) or 0.0,
        volume_1h_usd=_safe_float(raw.get("volume1h", raw.get("volume", 0))) or 0.0,
        volume_24h_usd=_safe_float(raw.get("volume", 0)) or 0.0,
        real_volume_24h_usd=_safe_float(raw.get("volume", 0)) or 0.0,
        buy_count_1h=buy_c,
        sell_count_1h=sell_c,
        buy_sell_ratio=round(buy_c / max(sell_c, 1), 4),
        age_seconds=age_sec,
        holder_count=_safe_int(raw.get("holder_count")),
        top10_holder_pct=_safe_float(raw.get("top10_holder_percent")) or 0.0,
        contract_renounced=bool(raw.get("is_renounced", False)),
        lp_burned=bool(raw.get("lp_burned", False)),
        is_honeypot=bool(raw.get("is_honeypot", False)),
        buy_tax=_safe_float(raw.get("buy_tax")) or 0.0,
        sell_tax=_safe_float(raw.get("sell_tax")) or 0.0,
        smart_buy_24h=_safe_int(raw.get("smart_buy_24h")),
        smart_sell_24h=_safe_int(raw.get("smart_sell_24h")),
    )


def apply_security_overlay(card: TokenCard, sec: dict) -> TokenCard:
    """Merge /v1/token/security response fields onto an existing TokenCard."""
    return card.model_copy(update={
        "contract_renounced": bool(sec.get("is_renounced")),
        "lp_burned": bool(sec.get("lp_burned")),
        "is_honeypot": bool(sec.get("is_honeypot")),
        "buy_tax": _safe_float(sec.get("buy_tax")) or card.buy_tax,
        "sell_tax": _safe_float(sec.get("sell_tax")) or card.sell_tax,
    })


def normalize_wallet(address: str, raw: dict) -> SmartMoneyWallet:
    trades_raw = raw.get("recent_trades", raw.get("trade_history", []))

    last_active: Optional[datetime] = None
    if raw.get("last_active"):
        try:
            last_active = datetime.fromtimestamp(int(raw["last_active"]), tz=timezone.utc)
        except (ValueError, TypeError):
            pass

    return SmartMoneyWallet(
        address=address,
        win_rate=_safe_float(raw.get("win_rate")) or 0.0,
        realized_pnl_usd=_safe_float(raw.get("realized_pnl")) or 0.0,
        unrealized_pnl_usd=_safe_float(raw.get("unrealized_pnl")) or 0.0,
        total_pnl_usd=_safe_float(raw.get("total_pnl")) or 0.0,
        avg_hold_hours=(_safe_float(raw.get("avg_hold_time")) or 0.0) / 3600,
        trade_count_30d=_safe_int(raw.get("trade_count")),
        wallet_type=raw.get("wallet_type", "unknown"),
        last_active=last_active,
        recent_trades=[_normalize_trade(t) for t in trades_raw[:20]],
    )


def _normalize_trade(t: dict) -> RecentTrade:
    ts = 0
    try:
        ts = int(t.get("timestamp", 0) or 0)
    except (ValueError, TypeError):
        pass

    return RecentTrade(
        mint=t.get("token_address", ""),
        symbol=t.get("symbol", ""),
        side=t.get("type", "buy").lower(),
        amount_usd=_safe_float(t.get("usd_amount")) or 0.0,
        pnl_usd=_safe_float(t.get("pnl")),
        timestamp=datetime.fromtimestamp(ts, tz=timezone.utc),
    )
