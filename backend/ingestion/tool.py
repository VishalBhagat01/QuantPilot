"""Data ingestion tools for real-time market data, company fundamentals, and trading signals."""

import time
import logging
from threading import Lock
from datetime import datetime, timedelta
import requests
import pandas as pd
from langchain_core.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun
from backend.core.config import settings

logger = logging.getLogger(__name__)

FINNHUB_KEY = settings.finnhub_api_key
ALPHA_KEY = settings.alphavantage_api_key
TIMEOUT = settings.http_timeout


class SimpleTTLCache:
    """Thread-safe in-memory cache with configurable TTL (seconds)."""
    def __init__(self, default_ttl_seconds: int = 60, max_size: int = 250):
        self.default_ttl = default_ttl_seconds
        self.max_size = max_size
        self._cache = {}
        self._lock = Lock()

    def get(self, key: str):
        with self._lock:
            item = self._cache.get(key)
            if not item:
                return None
            val, expiry = item
            if time.time() > expiry:
                del self._cache[key]
                return None
            return val

    def set(self, key: str, val, ttl_seconds: int = None):
        with self._lock:
            now = time.time()
            if len(self._cache) >= self.max_size:
                expired = [k for k, (_, exp) in self._cache.items() if now > exp]
                for k in expired:
                    del self._cache[k]
                if len(self._cache) >= self.max_size:
                    for k in list(self._cache.keys())[:int(self.max_size * 0.2)]:
                        del self._cache[k]
            ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
            self._cache[key] = (val, now + ttl)


# High-performance in-memory cache instances
_price_cache = SimpleTTLCache(default_ttl_seconds=60)      # 1 minute quote cache
_news_cache = SimpleTTLCache(default_ttl_seconds=300)      # 5 minutes news cache
_overview_cache = SimpleTTLCache(default_ttl_seconds=43200) # 12 hours fundamentals cache


def _safe_get(url: str, timeout: float = TIMEOUT) -> dict | list | None:
    """Safely perform an HTTP GET request with a strict timeout."""
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning(f"[API] Request failed for {url[:60]}...: {e}")
        return None


# ---------------------------------------------------------------------------
# Finnhub & Yahoo Finance Pricing / News Tools
# ---------------------------------------------------------------------------

@tool
def get_stock_price(symbol: str):
    """
    Retrieve the latest real-time stock quote for a given ticker symbol.
    Uses Finnhub with automatic fallback to Yahoo Finance.
    """
    clean_sym = symbol.strip().upper()

    # Fast cache lookup (sub-millisecond)
    cached = _price_cache.get(clean_sym)
    if cached:
        logger.info(f"[CACHE HIT] get_stock_price({clean_sym})")
        return cached

    # 1. Try Finnhub
    if FINNHUB_KEY:
        try:
            d = _safe_get(f"https://finnhub.io/api/v1/quote?symbol={clean_sym}&token={FINNHUB_KEY}")
            if isinstance(d, dict) and d.get("c") and d["c"] > 0:
                result = {
                    "symbol": clean_sym,
                    "current": float(d["c"]),
                    "high": float(d.get("h", d["c"])),
                    "low": float(d.get("l", d["c"])),
                    "open": float(d.get("o", d["c"])),
                    "prev_close": float(d.get("pc", d["c"])),
                    "timestamp": d.get("t", int(datetime.now().timestamp())),
                }
                _price_cache.set(clean_sym, result)
                return result
        except Exception:
            pass

    # 2. Fallback to Yahoo Finance
    try:
        import yfinance as yf
        ticker = yf.Ticker(clean_sym)
        info = ticker.fast_info
        current = float(info.last_price or 0.0)
        result = {
            "symbol": clean_sym,
            "current": round(current, 2),
            "high": round(float(getattr(info, "day_high", current) or current), 2),
            "low": round(float(getattr(info, "day_low", current) or current), 2),
            "open": round(float(getattr(info, "open", current) or current), 2),
            "prev_close": round(float(getattr(info, "previous_close", current) or current), 2),
            "timestamp": int(datetime.now().timestamp()),
        }
        _price_cache.set(clean_sym, result)
        return result
    except Exception as e:
        return {"symbol": clean_sym, "error": f"Failed to retrieve price for {clean_sym}: {str(e)}"}


@tool
def get_stock_news(symbol: str):
    """Fetch the most recent news articles related to a stock symbol."""
    clean_sym = symbol.strip().upper()

    cached = _news_cache.get(clean_sym)
    if cached:
        logger.info(f"[CACHE HIT] get_stock_news({clean_sym})")
        return cached

    # 1. Try Finnhub
    if FINNHUB_KEY:
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            one_month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            url = f"https://finnhub.io/api/v1/company-news?symbol={clean_sym}&from={one_month_ago}&to={today}&token={FINNHUB_KEY}"
            data = _safe_get(url)
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict) and "headline" in data[0]:
                results = [
                    {
                        "headline": n["headline"],
                        "summary": n.get("summary", ""),
                        "source": n.get("source", ""),
                        "url": n.get("url", ""),
                        "time": n.get("datetime", ""),
                    }
                    for n in data[:5]
                ]
                _news_cache.set(clean_sym, results)
                return results
        except Exception:
            pass

    # 2. Fallback to Yahoo Finance news
    try:
        import yfinance as yf
        ticker = yf.Ticker(clean_sym)
        news_items = ticker.news or []
        if news_items:
            results = []
            for n in news_items[:5]:
                content = n.get("content", {})
                results.append({
                    "headline": content.get("title") or n.get("title", f"News for {clean_sym}"),
                    "summary": content.get("summary") or n.get("summary", ""),
                    "source": content.get("provider", {}).get("displayName", "Yahoo Finance"),
                    "url": content.get("canonicalUrl", {}).get("url", ""),
                    "time": content.get("pubDate") or "",
                })
            _news_cache.set(clean_sym, results)
            return results
    except Exception:
        pass

    fallback = [{"headline": f"No recent news available for {clean_sym}.", "summary": "", "source": "", "url": "", "time": ""}]
    return fallback


@tool
def get_old_news(symbol: str):
    """Fetch historical company news across a broader time range."""
    clean_sym = symbol.strip().upper()
    if FINNHUB_KEY:
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            four_years_ago = (datetime.now() - timedelta(days=4 * 365)).strftime("%Y-%m-%d")
            url = f"https://finnhub.io/api/v1/company-news?symbol={clean_sym}&from={four_years_ago}&to={today}&token={FINNHUB_KEY}"
            data = _safe_get(url)
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                return data[:5]
        except Exception:
            pass
    return []


@tool
def search_tool(query: str):
    """Perform a live DuckDuckGo web search when real-time external info is needed."""
    try:
        search = DuckDuckGoSearchRun(region="us-en")
        return search.run(query)
    except Exception as e:
        return f"Search query failed: {e}"


# ---------------------------------------------------------------------------
# AlphaVantage Fundamentals & Market Tools
# ---------------------------------------------------------------------------

@tool
def get_stock_price2(symbol: str):
    """Retrieve latest daily adjusted OHLCV stock data (AlphaVantage)."""
    clean_sym = symbol.strip().upper()
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol={clean_sym}&apikey={ALPHA_KEY}"
    data = _safe_get(url)

    if not data or "Time Series (Daily)" not in data:
        # Fallback to get_stock_price
        return get_stock_price.invoke({"symbol": clean_sym})

    series = data["Time Series (Daily)"]
    latest_date = sorted(series.keys(), reverse=True)[0]
    latest = series[latest_date]

    return {
        "date": latest_date,
        "open": latest.get("1. open"),
        "high": latest.get("2. high"),
        "low": latest.get("3. low"),
        "close": latest.get("4. close"),
        "adj_close": latest.get("5. adjusted close"),
        "volume": latest.get("6. volume"),
    }


@tool
def get_stock_news2(symbol: str):
    """Retrieve news sentiment feed with polarity scores (AlphaVantage)."""
    clean_sym = symbol.strip().upper()
    url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={clean_sym}&apikey={ALPHA_KEY}"
    data = _safe_get(url)
    if data and "feed" in data:
        return data["feed"][:5]
    return get_stock_news.invoke({"symbol": clean_sym})


@tool
def company_inside_news(symbol: str, quarter: str = "2024Q1"):
    """Retrieve earnings call transcript for a specific quarter."""
    clean_sym = symbol.strip().upper()
    url = f"https://www.alphavantage.co/query?function=EARNINGS_CALL_TRANSCRIPT&symbol={clean_sym}&quarter={quarter}&apikey={ALPHA_KEY}"
    return _safe_get(url) or {"error": "Transcript unavailable"}


@tool
def top_gainers():
    """Retrieve top gaining, losing, and most active stocks."""
    url = f"https://www.alphavantage.co/query?function=TOP_GAINERS_LOSERS&apikey={ALPHA_KEY}"
    d = _safe_get(url)
    if d and "top_gainers" in d:
        return {
            "gainers": d.get("top_gainers", [])[:5],
            "losers": d.get("top_losers", [])[:5],
            "active": d.get("most_actively_traded", [])[:5],
        }
    return {"gainers": [], "losers": [], "active": []}


@tool
def company_overview(symbol: str):
    """Retrieve company fundamental and valuation metrics."""
    clean_sym = symbol.strip().upper()

    cached = _overview_cache.get(clean_sym)
    if cached:
        logger.info(f"[CACHE HIT] company_overview({clean_sym})")
        return cached

    url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={clean_sym}&apikey={ALPHA_KEY}"
    d = _safe_get(url)

    if d and "Name" in d:
        result = {
            "name": d.get("Name", clean_sym),
            "sector": d.get("Sector", "N/A"),
            "market_cap": d.get("MarketCapitalization", "N/A"),
            "pe": d.get("PERatio", "N/A"),
            "eps": d.get("EPS", "N/A"),
            "revenue": d.get("RevenueTTM", "N/A"),
            "profit_margin": d.get("ProfitMargin", "N/A"),
        }
        _overview_cache.set(clean_sym, result)
        return result

    # Fallback to yfinance
    try:
        import yfinance as yf
        info = yf.Ticker(clean_sym).info
        result = {
            "name": info.get("longName", clean_sym),
            "sector": info.get("sector", "N/A"),
            "market_cap": info.get("marketCap", "N/A"),
            "pe": info.get("trailingPE", "N/A"),
            "eps": info.get("trailingEps", "N/A"),
            "revenue": info.get("totalRevenue", "N/A"),
            "profit_margin": info.get("profitMargins", "N/A"),
        }
        _overview_cache.set(clean_sym, result)
        return result
    except Exception:
        return {"name": clean_sym, "sector": "N/A", "market_cap": "N/A", "pe": "N/A", "eps": "N/A", "revenue": "N/A", "profit_margin": "N/A"}


@tool
def annual_income_statement(symbol: str):
    """Retrieve annual and quarterly income statement reports."""
    clean_sym = symbol.strip().upper()
    url = f"https://www.alphavantage.co/query?function=INCOME_STATEMENT&symbol={clean_sym}&apikey={ALPHA_KEY}"
    d = _safe_get(url)
    if d and "annualReports" in d:
        return {
            "annual": d.get("annualReports", [])[:3],
            "quarterly": d.get("quarterlyReports", [])[:3],
        }
    return {"annual": [], "quarterly": []}


@tool
def earning_estimate(symbol: str):
    """Retrieve analyst earnings estimates and projections."""
    clean_sym = symbol.strip().upper()
    url = f"https://www.alphavantage.co/query?function=EARNINGS_ESTIMATES&symbol={clean_sym}&apikey={ALPHA_KEY}"
    return _safe_get(url) or {}


@tool
def future_expected_earning(symbol: str):
    """Retrieve upcoming earnings calendar events."""
    clean_sym = symbol.strip().upper()
    url = f"https://www.alphavantage.co/query?function=EARNINGS_CALENDAR&symbol={clean_sym}&horizon=3month&apikey={ALPHA_KEY}"
    return _safe_get(url) or {}


@tool
def get_gold_price():
    """Retrieve current gold spot price in USD (XAU/USD)."""
    url = f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=XAU&to_currency=USD&apikey={ALPHA_KEY}"
    return _safe_get(url) or {"error": "Gold price unavailable"}


@tool
def get_silver_price():
    """Retrieve current silver spot price in USD (XAG/USD)."""
    url = f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=XAG&to_currency=USD&apikey={ALPHA_KEY}"
    return _safe_get(url) or {"error": "Silver price unavailable"}


TIMEFRAME_CONFIG = {
    "1D": ("1d", "5m", "%H:%M", 60),
    "5D": ("5d", "15m", "%a %H:%M", 300),
    "1M": ("1mo", "1d", "%b %d", 1800),
    "6M": ("6mo", "1d", "%b %d", 3600),
    "1Y": ("1y", "1wk", "%b %y", 7200),
}

_chart_cache = SimpleTTLCache(default_ttl_seconds=300)


def get_stock_chart_data(symbol: str, timeframe: str = "1D"):
    """Fetch structured historical OHLC chart series for specified timeframe."""
    clean_sym = symbol.strip().upper()
    tf = timeframe.upper().strip()
    if tf not in TIMEFRAME_CONFIG:
        tf = "1D"

    cache_key = f"{clean_sym}:{tf}"
    cached = _chart_cache.get(cache_key)
    if cached:
        logger.info(f"[CACHE HIT] get_stock_chart_data({cache_key})")
        return cached

    period, interval, date_fmt, ttl = TIMEFRAME_CONFIG[tf]
    chart_data = []

    try:
        import yfinance as yf
        hist = yf.download(clean_sym, period=period, interval=interval, progress=False)
        if not hist.empty:
            closes = hist["Close"].squeeze()
            highs = hist["High"].squeeze() if "High" in hist else closes
            lows = hist["Low"].squeeze() if "Low" in hist else closes

            # Sample if points > 80 to maintain smooth chart render performance
            step = max(1, len(closes) // 70) if len(closes) > 80 else 1
            sampled = closes.iloc[::step]
            if sampled.index[-1] != closes.index[-1]:
                sampled = pd.concat([sampled, closes.iloc[[-1]]])

            for idx, val in sampled.items():
                time_str = idx.strftime(date_fmt) if hasattr(idx, "strftime") else str(idx)
                chart_data.append({
                    "time": time_str,
                    "price": round(float(val), 2)
                })

            first_val = float(closes.iloc[0])
            last_val = float(closes.iloc[-1])
            max_val = float(highs.max())
            min_val = float(lows.min())

            result = {
                "chart": chart_data,
                "first_price": round(first_val, 2),
                "last_price": round(last_val, 2),
                "period_high": round(max_val, 2),
                "period_low": round(min_val, 2),
                "timeframe": tf
            }
            _chart_cache.set(cache_key, result, ttl_seconds=ttl)
            return result
    except Exception as e:
        logger.warning(f"Error fetching chart data for {clean_sym} ({tf}): {e}")

    return {
        "chart": [],
        "first_price": None,
        "last_price": None,
        "period_high": None,
        "period_low": None,
        "timeframe": tf
    }


@tool
def get_stock_intraday_chart(symbol: str):
    """Retrieve intraday price series (5-minute interval) for charting."""
    data = get_stock_chart_data(symbol, timeframe="1D")
    return data.get("chart", [])


def fetch_stock_dashboard_data(symbol: str, timeframe: str = "1D"):
    """Directly fetches aggregated data for the dashboard widget with dynamic timeframe support."""
    clean_sym = symbol.strip().upper()
    quote = {}
    overview = {}

    try:
        quote = get_stock_price.invoke({"symbol": clean_sym})
    except Exception:
        pass

    try:
        overview = company_overview.invoke({"symbol": clean_sym})
    except Exception:
        overview = {}

    chart_info = get_stock_chart_data(clean_sym, timeframe=timeframe)
    chart = chart_info.get("chart", [])

    cur_price = quote.get("current") or chart_info.get("last_price")
    prev_close = quote.get("prev_close")

    tf = timeframe.upper().strip()
    if tf == "1D" and prev_close:
        change = round(cur_price - prev_close, 2) if cur_price else 0.0
        percent = round((change / prev_close) * 100, 2) if prev_close > 0 else 0.0
    elif chart_info.get("first_price") and cur_price:
        start_p = chart_info["first_price"]
        change = round(cur_price - start_p, 2)
        percent = round((change / start_p) * 100, 2) if start_p > 0 else 0.0
    else:
        change = round(cur_price - prev_close, 2) if cur_price and prev_close else 0.0
        percent = round((change / prev_close) * 100, 2) if prev_close and prev_close > 0 else 0.0

    high = chart_info.get("period_high") or quote.get("high")
    low = chart_info.get("period_low") or quote.get("low")
    open_price = chart_info.get("first_price") or quote.get("open")

    return {
        "symbol": clean_sym,
        "company": overview.get("name") or overview.get("Name") or clean_sym,
        "price": cur_price,
        "change": change,
        "percent": percent,
        "open": open_price,
        "high": high,
        "low": low,
        "prev_close": prev_close,
        "volume": quote.get("volume"),
        "market_cap": overview.get("market_cap") or overview.get("MarketCapitalization"),
        "chart": chart,
        "timeframe": tf
    }


@tool
def predict_stock_signal(symbol: str):
    """Generate a BUY/SELL/HOLD trading signal using technical indicators (SMA, RSI, MACD)."""
    clean_sym = symbol.strip().upper()
    df = None

    # 1. Try AlphaVantage
    if ALPHA_KEY:
        try:
            url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={clean_sym}&outputsize=compact&apikey={ALPHA_KEY}"
            data = _safe_get(url, timeout=5.0)
            if data and "Time Series (Daily)" in data:
                time_series = data["Time Series (Daily)"]
                dates = sorted(time_series.keys(), reverse=True)[:100]
                prices = [
                    {
                        "date": date,
                        "close": float(time_series[date]["4. close"]),
                        "open": float(time_series[date]["1. open"]),
                        "high": float(time_series[date]["2. high"]),
                        "low": float(time_series[date]["3. low"])
                    }
                    for date in reversed(dates)
                ]
                if prices:
                    df = pd.DataFrame(prices)
        except Exception:
            pass

    # 2. Fallback to yfinance
    if df is None or len(df) < 10:
        try:
            import yfinance as yf
            y_df = yf.download(clean_sym, period="6mo", interval="1d", progress=False)
            if not y_df.empty:
                df = pd.DataFrame({
                    "close": y_df["Close"].squeeze().astype(float),
                    "open": y_df["Open"].squeeze().astype(float),
                    "high": y_df["High"].squeeze().astype(float),
                    "low": y_df["Low"].squeeze().astype(float)
                }).dropna().reset_index(drop=True)
        except Exception:
            pass

    if df is None or len(df) < 5:
        return {
            "symbol": clean_sym,
            "signal": "HOLD",
            "confidence": "50%",
            "confidence_raw": 50,
            "reasoning": f"Insufficient historical data available for {clean_sym}.",
            "indicators": {}
        }

    sma_20 = float(df["close"].iloc[-20:].mean()) if len(df) >= 20 else float(df["close"].mean())
    sma_50 = float(df["close"].iloc[-50:].mean()) if len(df) >= 50 else float(df["close"].mean())

    closes = df["close"].values
    deltas = pd.Series(closes).diff()
    gains = (deltas.where(deltas > 0, 0)).rolling(window=14).mean()
    losses = (-deltas.where(deltas < 0, 0)).rolling(window=14).mean()
    rs = gains / losses.replace(0, 0.0001)
    rsi = 100 - (100 / (1 + rs))
    current_rsi = float(rsi.iloc[-1]) if len(rsi) > 0 and not pd.isna(rsi.iloc[-1]) else 50.0

    ema_12 = df["close"].ewm(span=12, adjust=False).mean()
    ema_26 = df["close"].ewm(span=26, adjust=False).mean()
    macd_line = ema_12 - ema_26
    macd_signal = macd_line.ewm(span=9, adjust=False).mean()
    macd_diff = macd_line - macd_signal
    current_macd = float(macd_diff.iloc[-1]) if len(macd_diff) > 0 and not pd.isna(macd_diff.iloc[-1]) else 0.0

    current_price = float(closes[-1])
    price_change = float(((current_price - closes[0]) / closes[0]) * 100)

    signal_score = 0
    reasons = []

    if current_price > sma_20 > sma_50:
        signal_score += 2
        reasons.append("Price above SMA20 above SMA50 (bullish)")
    elif current_price < sma_20 < sma_50:
        signal_score -= 2
        reasons.append("Price below SMA20 below SMA50 (bearish)")
    elif current_price > sma_20:
        signal_score += 1
        reasons.append("Price above SMA20")
    elif current_price < sma_20:
        signal_score -= 1
        reasons.append("Price below SMA20")

    if current_rsi < 30:
        signal_score += 1
        reasons.append(f"RSI oversold ({current_rsi:.1f})")
    elif current_rsi > 70:
        signal_score -= 1
        reasons.append(f"RSI overbought ({current_rsi:.1f})")

    if current_macd > 0:
        signal_score += 1
        reasons.append("MACD above signal line (bullish)")
    else:
        signal_score -= 1
        reasons.append("MACD below signal line (bearish)")

    if signal_score >= 2:
        signal = "BUY"
        confidence = min(90, 50 + abs(signal_score) * 10)
    elif signal_score <= -2:
        signal = "SELL"
        confidence = min(90, 50 + abs(signal_score) * 10)
    else:
        signal = "HOLD"
        confidence = 50

    return {
        "symbol": clean_sym,
        "signal": signal,
        "confidence": f"{confidence:.0f}%",
        "confidence_raw": confidence,
        "reasoning": " | ".join(reasons) if reasons else "Mixed signals, recommend holding.",
        "indicators": {
            "SMA_20": f"${sma_20:.2f}",
            "SMA_50": f"${sma_50:.2f}",
            "RSI_14": f"{current_rsi:.1f}",
            "MACD_diff": f"{current_macd:.4f}",
            "current_price": f"${current_price:.2f}",
            "price_change_3m": f"{price_change:.2f}%"
        }
    }


# ---------------------------------------------------------------------------
# Alpaca Broker Tools
# ---------------------------------------------------------------------------

@tool
def get_broker_account():
    """Get broker account information.

    Broker access is intentionally exposed through authenticated REST
    endpoints so the request's Supabase user can select the correct
    per-user Alpaca connection.
    """
    return {"error": "Use the authenticated /trading/account endpoint."}


@tool
def get_broker_positions():
    """Get all current open positions from the authenticated broker account."""
    return {"error": "Use the authenticated /trading/positions endpoint."}


@tool
def place_trade(symbol: str, qty: int, side: str, order_type: str = "market"):
    """Place a trade order.

    Order mutations require an authenticated user-scoped execution endpoint;
    the AI tool cannot safely infer which connected account should be used.
    """
    return {"error": "Order placement requires an authenticated user-scoped endpoint."}
    from backend.trading.broker import place_order
    return place_order(symbol=symbol, qty=qty, side=side, order_type=order_type)


@tool
def close_trade(symbol: str):
    """Close an entire open position for a given stock symbol."""
    from backend.trading.broker import close_position
    return close_position(symbol)
