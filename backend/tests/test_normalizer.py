import pytest

from services.normalizer import (
    apply_security_overlay,
    normalize_token,
    normalize_wallet,
)


def test_normalize_token_basic(raw_token):
    card = normalize_token(raw_token, "rank_1h")

    assert card.mint == "So11111111111111111111111111111111111111112"
    assert card.symbol == "TESTKOIN"
    assert card.source == "rank_1h"
    assert card.price_usd == pytest.approx(0.0012345)
    assert card.liquidity_usd == 85000.0
    assert card.market_cap_usd == 1200000.0
    assert card.holder_count == 1500
    assert card.top10_holder_pct == pytest.approx(35.5)
    assert card.buy_count_1h == 200
    assert card.sell_count_1h == 120
    assert card.buy_sell_ratio == pytest.approx(200 / 120, rel=1e-3)
    assert card.contract_renounced is True
    assert card.lp_burned is True
    assert card.is_honeypot is False
    assert card.smart_buy_24h == 12
    assert card.smart_sell_24h == 3


def test_normalize_token_missing_fields():
    raw = {"address": "AbCdEfG", "symbol": "X"}
    card = normalize_token(raw, "new")

    assert card.mint == "AbCdEfG"
    assert card.symbol == "X"
    assert card.price_usd == 0.0
    assert card.liquidity_usd == 0.0
    assert card.holder_count == 0
    assert card.age_seconds >= 0
    assert card.is_honeypot is False


def test_apply_security_overlay(raw_token, security_response):
    card = normalize_token(raw_token, "rank_1h")
    sec = security_response["data"]
    updated = apply_security_overlay(card, sec)

    assert updated.contract_renounced is True
    assert updated.lp_burned is True
    assert updated.is_honeypot is False
    # Original card should be unchanged (model_copy returns new instance)
    assert card.mint == updated.mint


def test_normalize_wallet(wallet_response):
    raw = wallet_response["data"]
    wallet = normalize_wallet("WalletAddr123", raw)

    assert wallet.address == "WalletAddr123"
    assert wallet.win_rate == pytest.approx(0.72)
    assert wallet.total_pnl_usd == pytest.approx(53000.0)
    assert wallet.avg_hold_hours == pytest.approx(14400 / 3600)
    assert wallet.trade_count_30d == 85
    assert wallet.wallet_type == "smart_money"
    assert len(wallet.recent_trades) == 1
    assert wallet.recent_trades[0].symbol == "TESTKOIN"
    assert wallet.recent_trades[0].side == "buy"
