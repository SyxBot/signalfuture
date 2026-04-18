import pytest
import httpx
import pytest_asyncio

from unittest.mock import AsyncMock, MagicMock, patch

from core.rate_limiter import RateLimiter
from gmgn.client import GMGNClient
from gmgn.exceptions import AuthError, RateLimitError, GMGNError


@pytest.fixture
def limiter():
    return RateLimiter(rate=100.0, burst=100)


@pytest.fixture
def client(limiter):
    return GMGNClient(limiter)


@pytest.mark.asyncio
async def test_get_success(client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"code": 0, "msg": "success", "data": {"rank": []}}

    with patch.object(client._http, "get", new=AsyncMock(return_value=mock_response)):
        result = await client.get("/defi/quotation/v1/rank/sol/swaps/1h")

    assert result["code"] == 0
    assert "data" in result


@pytest.mark.asyncio
async def test_get_raises_auth_error(client):
    mock_response = MagicMock()
    mock_response.status_code = 401

    with patch.object(client._http, "get", new=AsyncMock(return_value=mock_response)):
        with pytest.raises(AuthError):
            await client.get("/some/path")


@pytest.mark.asyncio
async def test_get_raises_rate_limit_error(client):
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.headers = {"Retry-After": "1"}

    with patch.object(client._http, "get", new=AsyncMock(return_value=mock_response)):
        with pytest.raises(RateLimitError):
            await client.get("/some/path", retries=1)


@pytest.mark.asyncio
async def test_get_raises_gmgn_error_on_nonzero_code(client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"code": 1, "msg": "internal error"}

    with patch.object(client._http, "get", new=AsyncMock(return_value=mock_response)):
        with pytest.raises(GMGNError):
            await client.get("/some/path")
