from typing import List

from fastapi import APIRouter, Depends

from api.deps import get_cache, get_filter_engine
from models.token_card import TokenCard
from services.filter_engine import FilterCriteria

router = APIRouter()


@router.post("/filters/apply", response_model=List[TokenCard])
async def apply_filters(
    criteria: FilterCriteria,
    cache=Depends(get_cache),
    engine=Depends(get_filter_engine),
):
    all_tokens = cache.get_all_tokens(limit=500)
    return engine.apply(all_tokens, criteria)
