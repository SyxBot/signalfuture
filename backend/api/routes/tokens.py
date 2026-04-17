from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import get_cache
from models.token_card import TokenCard

router = APIRouter()


@router.get("/tokens", response_model=List[TokenCard])
async def list_tokens(
    limit: int = Query(50, ge=1, le=200),
    cache=Depends(get_cache),
):
    return cache.get_all_tokens(limit=limit)


@router.get("/tokens/{mint}", response_model=TokenCard)
async def get_token(mint: str, cache=Depends(get_cache)):
    token = cache.get_token(mint)
    if token is None:
        raise HTTPException(status_code=404, detail="Token not found")
    return token
