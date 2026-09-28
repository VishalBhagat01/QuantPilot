"""Alpaca broker integration with safety guards."""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from backend.core.config import settings

logger = logging.getLogger(__name__)

_trading_client = None


def _get_trading_client():
    """Lazy-initializes the Alpaca TradingClient using centralized settings."""
    global _trading_client

    if _trading_client is None:
        try:
            from alpaca.trading.client import TradingClient
        except ImportError:
            raise ImportError("alpaca-py is not installed! Run: pip install alpaca-py")

        api_key = settings.alpaca_api_key
        secret_key = settings.alpaca_secret_key

        if not api_key or not secret_key:
            raise ValueError(
                "Alpaca API keys not configured! Add ALPACA_API_KEY and "
                "ALPACA_SECRET_KEY to your .env file."
            )

        paper = settings.alpaca_paper
        logger.info(f"[BROKER] Initializing Alpaca client ({'PAPER' if paper else 'LIVE'} trading)")
        _trading_client = TradingClient(api_key, secret_key, paper=paper)

    return _trading_client


def get_account_info() -> Dict[str, Any]:
    """Retrieves current Alpaca account overview."""
    try:
        client = _get_trading_client()
        account = client.get_account()

        return {
            "status": str(account.status),
            "cash": float(account.cash),
            "buying_power": float(account.buying_power),
            "equity": float(account.equity),
            "portfolio_value": float(account.portfolio_value) if account.portfolio_value else 0.0,
            "currency": str(account.currency),
            "paper": settings.alpaca_paper,
            "day_trade_count": int(account.daytrade_count) if account.daytrade_count else 0,
        }
    except Exception as e:
        logger.error(f"[BROKER] Failed to get account info: {e}")
        return {"error": str(e)}


def get_positions() -> List[Dict[str, Any]]:
    """Retrieves all open positions in the account."""
    try:
        client = _get_trading_client()
        positions = client.get_all_positions()

        return [
            {
                "symbol": str(pos.symbol),
                "qty": float(pos.qty),
                "side": str(pos.side),
                "market_value": float(pos.market_value) if pos.market_value else 0.0,
                "avg_entry_price": float(pos.avg_entry_price),
                "current_price": float(pos.current_price) if pos.current_price else 0.0,
                "unrealized_pl": float(pos.unrealized_pl) if pos.unrealized_pl else 0.0,
                "unrealized_pl_pct": float(pos.unrealized_plpc) if pos.unrealized_plpc else 0.0,
            }
            for pos in positions
        ]
    except Exception as e:
        logger.error(f"[BROKER] Failed to get positions: {e}")
        return [{"error": str(e)}]


def place_order(
    symbol: str,
    qty: int,
    side: str,
    order_type: str = "market",
    limit_price: Optional[float] = None,
    time_in_force: str = "gtc",
) -> Dict[str, Any]:
    """Places an order with safety validation."""
    side = side.lower().strip()
    if side not in ("buy", "sell"):
        raise ValueError(f"Invalid side: '{side}'. Must be 'buy' or 'sell'.")

    max_shares = settings.max_shares_per_order
    if qty > max_shares:
        raise ValueError(
            f"Order quantity ({qty}) exceeds maximum allowed ({max_shares} shares per order)."
        )

    if qty <= 0:
        raise ValueError(f"Order quantity must be positive, got: {qty}")

    order_type = order_type.lower().strip()
    if order_type not in ("market", "limit", "stop"):
        raise ValueError(f"Invalid order type: '{order_type}'. Must be 'market', 'limit', or 'stop'.")

    if order_type == "limit" and limit_price is None:
        raise ValueError("Limit orders require a limit_price parameter.")

    try:
        from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
        from alpaca.trading.enums import OrderSide, TimeInForce

        client = _get_trading_client()
        order_side = OrderSide.BUY if side == "buy" else OrderSide.SELL

        tif_map = {
            "gtc": TimeInForce.GTC,
            "day": TimeInForce.DAY,
            "ioc": TimeInForce.IOC,
            "fok": TimeInForce.FOK,
        }
        tif = tif_map.get(time_in_force.lower(), TimeInForce.GTC)

        if order_type == "market":
            order_data = MarketOrderRequest(
                symbol=symbol.upper(),
                qty=qty,
                side=order_side,
                time_in_force=tif,
            )
        elif order_type == "limit":
            order_data = LimitOrderRequest(
                symbol=symbol.upper(),
                qty=qty,
                side=order_side,
                time_in_force=tif,
                limit_price=limit_price,
            )
        else:
            order_data = MarketOrderRequest(
                symbol=symbol.upper(),
                qty=qty,
                side=order_side,
                time_in_force=tif,
            )

        order = client.submit_order(order_data=order_data)

        return {
            "order_id": str(order.id),
            "status": str(order.status),
            "symbol": str(order.symbol),
            "qty": str(order.qty),
            "side": str(order.side),
            "type": str(order.type),
            "submitted_at": str(order.submitted_at),
            "filled_avg_price": str(order.filled_avg_price) if order.filled_avg_price else None,
        }
    except Exception as e:
        logger.error(f"[BROKER] Order failed: {e}")
        return {"error": str(e), "symbol": symbol, "qty": qty, "side": side}


def close_position(symbol: str) -> Dict[str, Any]:
    """Closes an entire open position for a given symbol."""
    try:
        client = _get_trading_client()
        logger.info(f"[BROKER] Closing position for {symbol}...")
        order = client.close_position(symbol.upper())

        return {
            "order_id": str(order.id),
            "status": str(order.status),
            "symbol": str(order.symbol),
            "qty": str(order.qty),
            "side": str(order.side),
            "closed_at": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"[BROKER] Failed to close position for {symbol}: {e}")
        return {"error": str(e), "symbol": symbol}


def get_recent_orders(limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieves recent order history from Alpaca."""
    try:
        from alpaca.trading.requests import GetOrdersRequest
        from alpaca.trading.enums import QueryOrderStatus

        client = _get_trading_client()
        request = GetOrdersRequest(
            status=QueryOrderStatus.ALL,
            limit=limit,
        )
        orders = client.get_orders(filter=request)

        return [
            {
                "order_id": str(o.id),
                "symbol": str(o.symbol),
                "qty": str(o.qty),
                "side": str(o.side),
                "type": str(o.type),
                "status": str(o.status),
                "submitted_at": str(o.submitted_at),
                "filled_at": str(o.filled_at) if o.filled_at else None,
                "filled_avg_price": str(o.filled_avg_price) if o.filled_avg_price else None,
            }
            for o in orders
        ]
    except Exception as e:
        logger.error(f"[BROKER] Failed to get orders: {e}")
        return [{"error": str(e)}]
