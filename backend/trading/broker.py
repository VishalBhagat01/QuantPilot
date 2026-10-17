"""Alpaca broker integration with safety guards."""

import logging
from typing import Optional, List, Dict, Any
from backend.core.config import settings
from backend.trading.alpaca_oauth import request as user_request

logger = logging.getLogger(__name__)


def get_user_account_info(user_id: str) -> Dict[str, Any]:
    account = user_request(user_id, "GET", "/v2/account")
    return {
        "status": account.get("status"),
        "cash": float(account.get("cash", 0)),
        "buying_power": float(account.get("buying_power", 0)),
        "equity": float(account.get("equity", 0)),
        "portfolio_value": float(account.get("portfolio_value", 0)),
        "currency": account.get("currency"),
        "paper": True,
        "day_trade_count": int(account.get("daytrade_count", 0)),
    }


def get_user_positions(user_id: str) -> List[Dict[str, Any]]:
    positions = user_request(user_id, "GET", "/v2/positions")
    return [
        {
            "symbol": position.get("symbol"),
            "qty": float(position.get("qty", 0)),
            "side": position.get("side"),
            "market_value": float(position.get("market_value", 0)),
            "avg_entry_price": float(position.get("avg_entry_price", 0)),
            "current_price": float(position.get("current_price", 0)),
            "unrealized_pl": float(position.get("unrealized_pl", 0)),
            "unrealized_pl_pct": float(position.get("unrealized_plpc", 0)),
        }
        for position in positions
    ]


def get_user_recent_orders(user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    orders = user_request(user_id, "GET", "/v2/orders", params={"status": "all", "limit": limit})
    return [
        {
            "order_id": order.get("id"),
            "symbol": order.get("symbol"),
            "qty": order.get("qty"),
            "side": order.get("side"),
            "type": order.get("type"),
            "status": order.get("status"),
            "submitted_at": order.get("submitted_at"),
            "filled_at": order.get("filled_at"),
            "filled_avg_price": order.get("filled_avg_price"),
        }
        for order in orders
    ]


def place_user_order(
    user_id: str,
    symbol: str,
    qty: int,
    side: str,
    order_type: str = "market",
    limit_price: Optional[float] = None,
    time_in_force: str = "day",
) -> Dict[str, Any]:
    """Submit a validated order through the user's connected paper account."""
    clean_symbol = symbol.strip().upper()
    clean_side = side.strip().lower()
    clean_type = order_type.strip().lower()

    if not clean_symbol:
        raise ValueError("Symbol is required.")
    if clean_side not in {"buy", "sell"}:
        raise ValueError("Side must be 'buy' or 'sell'.")
    if not isinstance(qty, int) or qty <= 0:
        raise ValueError("Quantity must be a positive whole number.")
    if qty > settings.max_shares_per_order:
        raise ValueError(
            f"Order quantity exceeds the {settings.max_shares_per_order}-share safety limit."
        )
    if clean_type not in {"market", "limit"}:
        raise ValueError("Order type must be 'market' or 'limit'.")
    if clean_type == "limit" and (limit_price is None or limit_price <= 0):
        raise ValueError("A positive limit price is required for limit orders.")
    if time_in_force not in {"day", "gtc", "ioc", "fok"}:
        raise ValueError("Unsupported time-in-force value.")

    payload = {
        "symbol": clean_symbol,
        "qty": str(qty),
        "side": clean_side,
        "type": clean_type,
        "time_in_force": time_in_force,
    }
    if limit_price is not None:
        payload["limit_price"] = str(limit_price)

    order = user_request(user_id, "POST", "/v2/orders", json=payload)
    return {
        "order_id": order.get("id"),
        "status": order.get("status"),
        "symbol": order.get("symbol", clean_symbol),
        "qty": order.get("qty", str(qty)),
        "side": order.get("side", clean_side),
        "type": order.get("type", clean_type),
        "submitted_at": order.get("submitted_at"),
        "filled_avg_price": order.get("filled_avg_price"),
        "paper": True,
    }
