import time

from services.filter_engine import FilterCriteria, FilterEngine
from services.normalizer import normalize_token


def _make_token(**overrides):
    base = {
        "address": "mint_" + overrides.pop("suffix", "A"),
        "symbol": "TK",
        "price": 0.001,
        "liquidity": 10000,
        "volume": 50000,
        "market_cap": 500000,
        "holder_count": 500,
        "top10_holder_percent": 40.0,
        "buy_count": 100,
        "sell_count": 50,
        # Use a recent timestamp so age_seconds is small (within 30-day default)
        "pool_creation_timestamp": int(time.time()) - 3600,
        "is_renounced": False,
        "lp_burned": False,
        "is_honeypot": 0,
        "buy_tax": "0",
        "sell_tax": "0",
        "smart_buy_24h": 5,
    }
    base.update(overrides)
    return normalize_token(base, "test")


engine = FilterEngine()


def test_no_filters_returns_all():
    tokens = [_make_token(suffix=str(i)) for i in range(5)]
    result = engine.apply(tokens, FilterCriteria())
    assert len(result) == 5


def test_min_liquidity():
    tokens = [
        _make_token(suffix="A", liquidity=1000),
        _make_token(suffix="B", liquidity=20000),
    ]
    result = engine.apply(tokens, FilterCriteria(min_liquidity_usd=5000))
    assert len(result) == 1
    assert result[0].mint == "mint_B"


def test_market_cap_range():
    tokens = [
        _make_token(suffix="A", market_cap=100000),
        _make_token(suffix="B", market_cap=500000),
        _make_token(suffix="C", market_cap=2000000),
    ]
    result = engine.apply(tokens, FilterCriteria(min_market_cap_usd=200000, max_market_cap_usd=1000000))
    assert len(result) == 1
    assert result[0].mint == "mint_B"


def test_require_renounced():
    tokens = [
        _make_token(suffix="A", is_renounced=False),
        _make_token(suffix="B", is_renounced=True),
    ]
    result = engine.apply(tokens, FilterCriteria(require_renounced=True))
    assert len(result) == 1
    assert result[0].mint == "mint_B"


def test_exclude_honeypots():
    tokens = [
        _make_token(suffix="A", is_honeypot=1),
        _make_token(suffix="B", is_honeypot=0),
    ]
    result = engine.apply(tokens, FilterCriteria(exclude_honeypots=True))
    assert len(result) == 1
    assert result[0].mint == "mint_B"


def test_min_smart_buy_24h():
    tokens = [
        _make_token(suffix="A", smart_buy_24h=2),
        _make_token(suffix="B", smart_buy_24h=10),
    ]
    result = engine.apply(tokens, FilterCriteria(min_smart_buy_24h=5))
    assert len(result) == 1
    assert result[0].mint == "mint_B"
