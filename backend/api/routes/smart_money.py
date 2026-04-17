from typing import List

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_cache
from models.smart_money import SmartMoneyWallet

router = APIRouter()


@router.get("/smart_money", response_model=List[SmartMoneyWallet])
async def list_smart_money(cache=Depends(get_cache)):
    return cache.get_all_wallets(limit=50)


@router.get("/wallets/{address}", response_model=SmartMoneyWallet)
async def get_wallet(address: str, cache=Depends(get_cache)):
    wallet = cache.get_wallet(address)
    if wallet is None:
        raise HTTPException(status_code=404, detail="Wallet not found or expired")
    return wallet
