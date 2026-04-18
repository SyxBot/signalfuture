from typing import List

from pydantic import BaseModel

from models.token_card import TokenCard


class FilterCriteria(BaseModel):
    min_real_volume_usd: float = 0.0
    min_liquidity_usd: float = 0.0
    min_market_cap_usd: float = 0.0
    max_market_cap_usd: float = float("inf")
    max_age_seconds: int = 86400 * 30
    min_holder_count: int = 0
    max_top10_holder_pct: float = 100.0
    min_buy_sell_ratio: float = 0.0
    require_renounced: bool = False
    require_lp_burned: bool = False
    exclude_honeypots: bool = True
    max_buy_tax: float = 100.0
    max_sell_tax: float = 100.0
    min_smart_buy_24h: int = 0
    min_smart_money_count: int = 0


class FilterEngine:
    def apply(self, tokens: List[TokenCard], criteria: FilterCriteria) -> List[TokenCard]:
        result = []
        for t in tokens:
            if t.real_volume_24h_usd < criteria.min_real_volume_usd:
                continue
            if t.liquidity_usd < criteria.min_liquidity_usd:
                continue
            if t.market_cap_usd is not None:
                if t.market_cap_usd < criteria.min_market_cap_usd:
                    continue
                if t.market_cap_usd > criteria.max_market_cap_usd:
                    continue
            if t.age_seconds > criteria.max_age_seconds:
                continue
            if t.holder_count < criteria.min_holder_count:
                continue
            if t.top10_holder_pct > criteria.max_top10_holder_pct:
                continue
            if t.buy_sell_ratio < criteria.min_buy_sell_ratio:
                continue
            if criteria.require_renounced and not t.contract_renounced:
                continue
            if criteria.require_lp_burned and not t.lp_burned:
                continue
            if criteria.exclude_honeypots and t.is_honeypot:
                continue
            if t.buy_tax > criteria.max_buy_tax:
                continue
            if t.sell_tax > criteria.max_sell_tax:
                continue
            if t.smart_buy_24h < criteria.min_smart_buy_24h:
                continue
            if t.smart_money_count < criteria.min_smart_money_count:
                continue
            result.append(t)
        return result
