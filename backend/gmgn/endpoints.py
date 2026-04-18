BASE_URL = "https://gmgn.ai"

# Trending / ranked tokens — time_period: 1m | 5m | 1h | 6h | 24h
RANK_SWAPS = "/defi/quotation/v1/rank/sol/swaps/{time_period}"

# Trenches (new / almost-bonded / migrated)
NEW_TOKENS = "/v1/trenches/new"
ALMOST_BONDED = "/v1/trenches/almost_bonded"
MIGRATED = "/v1/trenches/migrated"

# Per-token detail  — params: chain=sol&address={mint}
TOKEN_INFO = "/v1/token/info"
TOKEN_SECURITY = "/v1/token/security"

# Wallet stats — params: chain=sol&address={wallet}
WALLET_STATS = "/v1/user/stats"

# WebSocket
WS_URL = "wss://gmgn.ai/ws"

# Default query-param bundles
RANK_PARAMS = {"orderby": "volume", "direction": "desc"}
CHAIN_SOL = {"chain": "sol"}
