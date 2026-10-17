"""Trading terminal and local technical scanner endpoints."""

import datetime
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.auth import verify_user
from backend.trading.broker import (
    get_user_account_info,
    get_user_positions,
    get_user_recent_orders,
    place_user_order,
)
from backend.trading.technical_scanner import scan_market, scan_symbol

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/trading", tags=["trading"])


class OrderRequest(BaseModel):
    """Validated paper-order request."""

    symbol: str = Field(min_length=1, max_length=10)
    qty: int = Field(gt=0)
    side: str
    order_type: str = "market"
    limit_price: Optional[float] = None
    time_in_force: str = "day"


def _get_user_id(user) -> str:
    return user.id if hasattr(user, "id") else user.get("id")


@router.get("/account")
def get_trading_account(user=Depends(verify_user)):
    """Return Alpaca trading account details."""
    try:
        return get_user_account_info(_get_user_id(user))
    except Exception as exc:
        logger.error("[ERROR] Trading account fetch failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/positions")
def get_trading_positions(user=Depends(verify_user)):
    """Return all open Alpaca positions."""
    try:
        return get_user_positions(_get_user_id(user))
    except Exception as exc:
        logger.error("[ERROR] Positions fetch failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/orders")
def get_trading_orders(user=Depends(verify_user)):
    """Return recent Alpaca orders."""
    try:
        return get_user_recent_orders(_get_user_id(user), limit=10)
    except Exception as exc:
        logger.error("[ERROR] Orders fetch failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/orders")
def submit_trading_order(payload: OrderRequest, user=Depends(verify_user)):
    """Submit a paper order for the authenticated user's connected Alpaca account."""
    try:
        return place_user_order(user_id=_get_user_id(user), **payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("[ERROR] Order submission failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/scan/{symbol}")
def scan_symbol_endpoint(symbol: str, user=Depends(verify_user)):
    """Run the local rule-based technical scanner for one ticker."""
    clean_symbol = symbol.strip().upper()
    if not clean_symbol:
        raise HTTPException(status_code=400, detail="Invalid ticker symbol")

    result = scan_symbol(clean_symbol).as_dict()
    result["patterns"] = []
    result["timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return result


@router.post("/market-scan")
def scan_market_endpoint(symbols: Optional[str] = None, user=Depends(verify_user)):
    """Scan and rank a comma-separated ticker universe."""
    requested_symbols = (
        [symbol.strip() for symbol in symbols.split(",") if symbol.strip()]
        if symbols
        else None
    )
    if requested_symbols is not None and not requested_symbols:
        raise HTTPException(status_code=400, detail="Provide at least one ticker symbol")
    if requested_symbols is not None and len(requested_symbols) > 50:
        raise HTTPException(status_code=400, detail="Scan is limited to 50 ticker symbols")

    try:
        return {
            "results": scan_market(requested_symbols),
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.error("[ERROR] Market scan failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
