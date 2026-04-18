import time

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from main import app
from services.normalizer import normalize_token
from services.filter_engine import FilterEngine


def _mock_cache(tokens=None, wallets=None):
    cache = MagicMock()
    cache.get_all_tokens.return_value = tokens or []
    cache.get_token.return_value = (tokens or [None])[0]
    cache.get_all_wallets.return_value = wallets or []
    cache.get_wallet.return_value = (wallets or [None])[0]
    return cache


def _sample_token():
    return normalize_token({
        "address": "AbCdEfGhIjKlMnOpQrStUvWxYz12345678901234",
        "symbol": "SMPL",
        "name": "Sample Token",
        "price": 0.0001,
        "liquidity": 25000,
        "volume": 100000,
        "market_cap": 800000,
        "holder_count": 800,
        "top10_holder_percent": 25.0,
        "buy_count": 300,
        "sell_count": 100,
        "pool_creation_timestamp": int(time.time()) - 3600,
        "is_renounced": True,
        "lp_burned": False,
        "is_honeypot": 0,
        "buy_tax": "0",
        "sell_tax": "0",
        "smart_buy_24h": 8,
    }, "rank_1h")


@pytest.fixture
def test_client():
    token = _sample_token()

    with TestClient(app, raise_server_exceptions=True) as c:
        # Override state AFTER lifespan startup so our mock isn't overwritten
        cache = _mock_cache(tokens=[token])
        c.app.state.cache = cache
        c.app.state.filter_engine = FilterEngine()
        feed_mock = MagicMock()
        feed_mock.subscribers = []
        c.app.state.feed_service = feed_mock
        yield c


def test_health(test_client):
    resp = test_client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_list_tokens(test_client):
    resp = test_client.get("/api/tokens?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["symbol"] == "SMPL"


def test_get_token(test_client):
    resp = test_client.get("/api/tokens/AbCdEfGhIjKlMnOpQrStUvWxYz12345678901234")
    assert resp.status_code == 200
    assert resp.json()["mint"] == "AbCdEfGhIjKlMnOpQrStUvWxYz12345678901234"


def test_filters_apply(test_client):
    resp = test_client.post("/api/filters/apply", json={
        "min_liquidity_usd": 1000,
        "exclude_honeypots": True,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert data[0]["symbol"] == "SMPL"


def test_filters_excludes_honeypot(test_client):
    honeypot = normalize_token({"address": "HONEY", "symbol": "HP", "is_honeypot": 1}, "test")
    test_client.app.state.cache.get_all_tokens.return_value = [honeypot]

    resp = test_client.post("/api/filters/apply", json={"exclude_honeypots": True})
    assert resp.status_code == 200
    assert resp.json() == []
