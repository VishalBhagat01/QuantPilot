"""Alpaca broker integration with lightweight safety guards."""

import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

MAX_SHARES_PER_ORDER = 100       # Max shares in a single order
MAX_ORDER_VALUE_USD = 10_000     # Max dollar value of a single order

_trading_client = None


def _get_trading_client():
    """
    Lazy-initializes the Alpaca TradingClient.
    
    Reads credentials from environment variables:
      - ALPACA_API_KEY: Your Alpaca API key
      - ALPACA_SECRET_KEY: Your Alpaca secret key
      - ALPACA_PAPER: "true" for paper trading (default), "false" for live
    
    Returns:
        alpaca.trading.client.TradingClient instance
    
    Raises:
        ValueError: If API keys are not configured
        ImportError: If alpaca-py is not installed
    """
    global _trading_client
    
    if _trading_client is None:
        try:
            from alpaca.trading.client import TradingClient
        except ImportError:
            raise ImportError(
                "alpaca-py is not installed! Run: pip install alpaca-py"
            )
        
        api_key = os.getenv("ALPACA_API_KEY")
        secret_key = os.getenv("ALPACA_SECRET_KEY")
        
        if not api_key or not secret_key:
            raise ValueError(
                "Alpaca API keys not configured! Add ALPACA_API_KEY and "
                "ALPACA_SECRET_KEY to your .env file. Sign up free at "
                "https://alpaca.markets"
            )
        
        paper = os.getenv("ALPACA_PAPER", "true").lower() == "true"
        
        logger.info(
            f"[BROKER] Initializing Alpaca client "
            f"({'PAPER' if paper else 'LIVE'} trading)"
        )
        
        _trading_client = TradingClient(api_key, secret_key, paper=paper)
        logger.info("[BROKER] Alpaca client initialized successfully!")
    
    return _trading_client


def get_account_info() -> Dict[str, Any]:
    """
    Retrieves the current Alpaca trading account information.
    
    Returns:
        Dictionary containing:
        - status: Account status (e.g., "ACTIVE")
        - cash: Available cash balance
        - buying_power: Total buying power available
        - equity: Total account equity (cash + positions value)
        - portfolio_value: Current portfolio market value
        - currency: Account currency (usually "USD")
        - paper: Whether this is a paper trading account
        - day_trade_count: Number of day trades in the last 5 days
    """
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
            "paper": os.getenv("ALPACA_PAPER", "true").lower() == "true",
            "day_trade_count": int(account.daytrade_count) if account.daytrade_count else 0,
        }
    except Exception as e:
        logger.error(f"[BROKER] Failed to get account info: {e}")
        return {"error": str(e)}


def get_positions() -> List[Dict[str, Any]]:
    """
    Retrieves all open positions in the account.
    
    Returns:
        List of position dictionaries, each containing:
        - symbol: Stock ticker
        - qty: Number of shares held
        - side: "long" or "short"
        - market_value: Current market value of the position
        - avg_entry_price: Average price paid per share
        - current_price: Current market price
        - unrealized_pl: Unrealized profit/loss in dollars
        - unrealized_pl_pct: Unrealized P&L as a percentage
    """
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
    """
    Places a trade order via Alpaca.
    
    SAFETY CHECKS:
    1. Quantity cannot exceed MAX_SHARES_PER_ORDER (100)
    2. Order type must be valid ("market", "limit", "stop")
    3. Side must be "buy" or "sell"
    4. Limit orders require a limit_price
    
    Args:
        symbol: Stock ticker (e.g., "AAPL")
        qty: Number of shares to trade
        side: "buy" or "sell"
        order_type: "market" (default), "limit", or "stop"
        limit_price: Required for limit orders, price per share
        time_in_force: "gtc" (good til cancelled), "day", "ioc", "fok"
    
    Returns:
        Dictionary with order details:
        - order_id: Unique order identifier
        - status: Order status ("new", "filled", "cancelled", etc.)
        - symbol: Stock ticker
        - qty: Shares ordered
        - side: "buy" or "sell"
        - type: Order type
        - submitted_at: Timestamp
        - filled_avg_price: Average fill price (if filled)
    
    Raises:
        ValueError: If safety checks fail (qty too large, invalid params)
    """
    side = side.lower().strip()
    if side not in ("buy", "sell"):
        raise ValueError(f"Invalid side: '{side}'. Must be 'buy' or 'sell'.")
    
    if qty > MAX_SHARES_PER_ORDER:
        raise ValueError(
            f"Order quantity ({qty}) exceeds maximum allowed "
            f"({MAX_SHARES_PER_ORDER} shares per order). "
            f"Reduce quantity or adjust MAX_SHARES_PER_ORDER."
        )
    
    if qty <= 0:
        raise ValueError(f"Order quantity must be positive, got: {qty}")
    
    order_type = order_type.lower().strip()
    if order_type not in ("market", "limit", "stop"):
        raise ValueError(
            f"Invalid order type: '{order_type}'. "
            f"Must be 'market', 'limit', or 'stop'."
        )
    
    if order_type == "limit" and limit_price is None:
        raise ValueError("Limit orders require a limit_price parameter.")
    
    logger.info(
        f"[BROKER] Placing {side.upper()} order: "
        f"{qty} shares of {symbol} ({order_type})"
    )
    
    try:
        from alpaca.trading.requests import (
            MarketOrderRequest,
            LimitOrderRequest,
        )
        from alpaca.trading.enums import OrderSide, TimeInForce
        
        client = _get_trading_client()
        
        order_side = OrderSide.BUY if side == "buy" else OrderSide.SELL
        
        tif_map = {
            "gtc": TimeInForce.GTC,    # Good Til Cancelled
            "day": TimeInForce.DAY,    # Day order
            "ioc": TimeInForce.IOC,    # Immediate or Cancel
            "fok": TimeInForce.FOK,    # Fill or Kill
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
        
        result = {
            "order_id": str(order.id),
            "status": str(order.status),
            "symbol": str(order.symbol),
            "qty": str(order.qty),
            "side": str(order.side),
            "type": str(order.type),
            "submitted_at": str(order.submitted_at),
            "filled_avg_price": str(order.filled_avg_price) if order.filled_avg_price else None,
        }
        
        logger.info(f"[BROKER] Order placed successfully: {result['order_id']}")
        return result
        
    except Exception as e:
        logger.error(f"[BROKER] Order failed: {e}")
        return {"error": str(e), "symbol": symbol, "qty": qty, "side": side}


def close_position(symbol: str) -> Dict[str, Any]:
    """
    Closes an entire open position for a given symbol.
    
    This sells all shares (for long positions) or covers all shares
    (for short positions) at market price.
    
    Args:
        symbol: Stock ticker to close the position for
    
    Returns:
        Dictionary with close order details or error message
    """
    try:
        client = _get_trading_client()
        
        logger.info(f"[BROKER] Closing position for {symbol}...")
        order = client.close_position(symbol.upper())
        
        result = {
            "order_id": str(order.id),
            "status": str(order.status),
            "symbol": str(order.symbol),
            "qty": str(order.qty),
            "side": str(order.side),
            "closed_at": datetime.now().isoformat(),
        }
        
        logger.info(f"[BROKER] Position closed: {symbol}")
        return result
        
    except Exception as e:
        logger.error(f"[BROKER] Failed to close position for {symbol}: {e}")
        return {"error": str(e), "symbol": symbol}


def get_recent_orders(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Retrieves recent order history from Alpaca.
    
    Args:
        limit: Maximum number of orders to return (default: 10)
    
    Returns:
        List of order dictionaries, most recent first
    """
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
