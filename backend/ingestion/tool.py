import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun

load_dotenv()

FINNHUB_KEY = os.getenv("FINNHUB_API_KEY")
ALPHA_KEY = os.getenv("ALPHAADVANTAGE_API_KEY")


@tool
def get_stock_price(symbol: str):
    """
    Retrieve the latest real-time stock quote for a given ticker symbol.

    Use this tool when the agent needs current intraday market pricing data.

    Args:
        symbol: Stock ticker symbol (example: AAPL, MSFT, TSLA)

    Returns:
        Dictionary containing:
        - symbol → ticker
        - current → last traded price
        - high → session high
        - low → session low
        - open → opening price
        - prev_close → previous close
        - timestamp → quote time
    """
    d = requests.get(
        f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_KEY}"
    ).json()

    return {
        "symbol": symbol,
        "current": d["c"],
        "high": d["h"],
        "low": d["l"],
        "open": d["o"],
        "prev_close": d["pc"],
        "timestamp": d["t"],
    }


@tool
def get_stock_news(symbol: str):
    """
    Fetch the most recent news articles related to a stock symbol.

    Use this tool when the agent needs current company developments,
    headlines, or event-driven signals.

    Args:
        symbol: Stock ticker symbol

    Returns:
        List of up to 5 news objects with:
        - headline
        - summary
        - source
        - url
        - publish time
    """
    today = datetime.now().strftime("%Y-%m-%d")
    one_month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    data = requests.get(
        f"https://finnhub.io/api/v1/company-news?symbol={symbol}&from={one_month_ago}&to={today}&token={FINNHUB_KEY}"
    ).json()

    return [
        {
            "headline": n["headline"],
            "summary": n["summary"],
            "source": n["source"],
            "url": n["url"],
            "time": n["datetime"],
        }
        for n in data[:5]
    ]


@tool
def get_old_news(symbol: str):
    """
    Fetch historical company news across a broader time range.

    Use this tool when the agent needs background context,
    long-term sentiment, or past events.

    Args:
        symbol: Stock ticker symbol

    Returns:
        List of 5 historical news records from Finnhub.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    four_years_ago = (datetime.now() - timedelta(days=4*365)).strftime("%Y-%m-%d")
    data = requests.get(
        f"https://finnhub.io/api/v1/company-news?symbol={symbol}&from={four_years_ago}&to={today}&token={FINNHUB_KEY}"
    ).json()

    return data[:5]


@tool
def search_tool(query: str):
    """
    Perform a live DuckDuckGo web search.

    Use this tool when required information is not available
    through market APIs or internal model knowledge.

    Args:
        query: Natural language search query

    Returns:
        Aggregated search summary text.
    """
    search = DuckDuckGoSearchRun(region="us-en")
    return search.run(query)


@tool
def get_stock_price2(symbol: str):
    """
    Retrieve latest daily adjusted OHLCV stock data.

    Use this tool for historical price reference,
    chart analysis, or technical reasoning.

    Args:
        symbol: Stock ticker

    Returns:
        Dictionary containing most recent daily bar:
        - date
        - open
        - high
        - low
        - close
        - adjusted close
        - volume
    """
    data = requests.get(
        f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol={symbol}&apikey={ALPHA_KEY}"
    ).json()

    series = data["Time Series (Daily)"]
    latest_date = sorted(series.keys(), reverse=True)[0]
    latest = series[latest_date]

    return {
        "date": latest_date,
        "open": latest["1. open"],
        "high": latest["2. high"],
        "low": latest["3. low"],
        "close": latest["4. close"],
        "adj_close": latest["5. adjusted close"],
        "volume": latest["6. volume"],
    }


@tool
def get_stock_news2(symbol: str):
    """
    Retrieve news sentiment feed for a stock.

    Use this tool when sentiment scoring
    and narrative polarity are required.

    Args:
        symbol: Stock ticker

    Returns:
        List of top 5 sentiment-scored news entries.
    """
    data = requests.get(
        f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={symbol}&apikey={ALPHA_KEY}"
    ).json()

    return data["feed"][:5]


@tool
def company_inside_news(symbol: str, quarter: str = "2024Q1"):
    """
    Retrieve earnings call transcript for a specific quarter.

    Use this tool for qualitative management analysis,
    forward guidance, and executive commentary.

    Args:
        symbol: Stock ticker
        quarter: Quarter string like YYYYQ1

    Returns:
        Transcript JSON payload.
    """
    return requests.get(
        f"https://www.alphavantage.co/query?function=EARNINGS_CALL_TRANSCRIPT&symbol={symbol}&quarter={quarter}&apikey={ALPHA_KEY}"
    ).json()


@tool
def top_gainers():
    """
    Retrieve top gaining, losing, and most active stocks.

    Use this tool for market scanning and volatility discovery.

    Returns:
        Dictionary with:
        - gainers list
        - losers list
        - most active list
    """
    d = requests.get(
        f"https://www.alphavantage.co/query?function=TOP_GAINERS_LOSERS&apikey={ALPHA_KEY}"
    ).json()

    return {
        "gainers": d["top_gainers"][:5],
        "losers": d["top_losers"][:5],
        "active": d["most_actively_traded"][:5],
    }


@tool
def company_overview(symbol: str):
    """
    Retrieve company fundamental and valuation metrics.

    Use this tool for profiling and valuation reasoning.

    Args:
        symbol: Stock ticker

    Returns:
        Dictionary containing:
        - company name
        - sector
        - market cap
        - PE ratio
        - EPS
        - revenue
        - profit margin
    """
    d = requests.get(
        f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={symbol}&apikey={ALPHA_KEY}"
    ).json()

    return {
        "name": d["Name"],
        "sector": d["Sector"],
        "market_cap": d["MarketCapitalization"],
        "pe": d["PERatio"],
        "eps": d["EPS"],
        "revenue": d["RevenueTTM"],
        "profit_margin": d["ProfitMargin"],
    }


@tool
def annual_income_statement(symbol: str):
    """
    Retrieve annual and quarterly income statement reports.

    Use this tool for profitability and revenue trend analysis.

    Args:
        symbol: Stock ticker

    Returns:
        Dictionary containing:
        - top 3 annual reports
        - top 3 quarterly reports
    """
    d = requests.get(
        f"https://www.alphavantage.co/query?function=INCOME_STATEMENT&symbol={symbol}&apikey={ALPHA_KEY}"
    ).json()

    return {
        "annual": d["annualReports"][:3],
        "quarterly": d["quarterlyReports"][:3],
    }


@tool
def earning_estimate(symbol: str):
    """
    Retrieve analyst earnings estimates and projections.

    Use this tool for forward expectation comparison.

    Args:
        symbol: Stock ticker

    Returns:
        Earnings estimate dataset JSON.
    """
    return requests.get(
        f"https://www.alphavantage.co/query?function=EARNINGS_ESTIMATES&symbol={symbol}&apikey={ALPHA_KEY}"
    ).json()


@tool
def future_expected_earning(symbol: str):
    """
    Retrieve upcoming earnings calendar events.

    Use this tool for event-driven trading logic.

    Args:
        symbol: Stock ticker

    Returns:
        Earnings calendar JSON data.
    """
    return requests.get(
        f"https://www.alphavantage.co/query?function=EARNINGS_CALENDAR&symbol={symbol}&horizon=3month&apikey={ALPHA_KEY}"
    ).json()


@tool
def get_gold_price():
    """
    Retrieve current gold spot price in USD.

    Use this tool for commodity tracking and macro analysis.

    Returns:
        Dictionary with current exchange rate for XAU/USD.
    """
    url = f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=XAU&to_currency=USD&apikey={ALPHA_KEY}"
    response = requests.get(url)
    return response.json()


@tool
def get_silver_price():
    """
    Retrieve current silver spot price in USD.

    Use this tool for commodity tracking and macro analysis.

    Returns:
        Dictionary with current exchange rate for XAG/USD.
    """
    url = f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=XAG&to_currency=USD&apikey={ALPHA_KEY}"
    response = requests.get(url)
    return response.json()
@tool
def get_stock_intraday_chart(symbol: str):
    """
    Retrieve intraday price series (5-minute interval) for charting.

    Use this tool when the agent needs granular price history for
    the current trading session.

    Args:
        symbol: Stock ticker
    
    Returns:
        List of dicts with 'time' (HH:MM) and 'price' (float) keys.
        If API fails, returns empty list or generates synthetic data.
    """
    try:
        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={symbol}&interval=5min&outputsize=small&apikey={ALPHA_KEY}"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        # Check for API errors
        if "Error Message" in data:
            print(f"[CHART] API Error for {symbol}: {data['Error Message']}", flush=True)
            return []
        if "Information" in data:
            print(f"[CHART] API Rate limit for {symbol}: {data['Information']}", flush=True)
            return []
        
        time_series = data.get("Time Series (5min)", {})
        if not time_series:
            print(f"[CHART] No intraday data available for {symbol}", flush=True)
            return []
        
        chart_data = []
        
        # Get last 50 data points and reverse to chronological order
        for timestamp in sorted(time_series.keys())[-50:]:
            try:
                ohlc = time_series[timestamp]
                chart_data.append({
                    "time": timestamp.split(" ")[1][:5],  # HH:MM
                    "price": float(ohlc.get("4. close", ohlc.get("1. open", 0)))
                })
            except (ValueError, KeyError) as e:
                print(f"[CHART] Error parsing data point for {symbol}: {e}", flush=True)
                continue
        
        print(f"[CHART] Retrieved {len(chart_data)} intraday points for {symbol}", flush=True)
        return chart_data
        
    except requests.exceptions.Timeout:
        print(f"[CHART] Timeout fetching data for {symbol}", flush=True)
        return []
    except Exception as e:
        print(f"[CHART] Error fetching intraday chart for {symbol}: {e}", flush=True)
        return []


def fetch_stock_dashboard_data(symbol: str):
    """
    Directly fetches aggregated data for the dashboard widget.
    Bypasses LLM for performance and quota management.
    """
    print(f">>> [DASHBOARD] Consolidating data for {symbol}...", flush=True)
    
    quote = {}
    chart = []
    overview = {}
    
    try:
        quote = get_stock_price.invoke({"symbol": symbol})
        print(f">>> [DASHBOARD] Price fetched: ${quote.get('current')}", flush=True)
    except Exception as e:
        print(f">>> [DASHBOARD] Price fetch failed: {e}", flush=True)
        
    try:
        chart = get_stock_intraday_chart.invoke({"symbol": symbol})
        print(f">>> [DASHBOARD] Chart fetched: {len(chart)} points", flush=True)
    except Exception as e:
        print(f">>> [DASHBOARD] Chart fetch failed: {e}", flush=True)
        chart = []
        
    try:
        overview = company_overview.invoke({"symbol": symbol})
        print(f">>> [DASHBOARD] Overview fetched: {overview.get('name', 'N/A')}", flush=True)
    except Exception as e:
        print(f">>> [DASHBOARD] Overview fetch failed: {e}", flush=True)

    result = {
        "symbol": symbol,
        "company": overview.get("Name", symbol),
        "price": quote.get("current"),
        "change": quote.get("current") - quote.get("prev_close") if quote.get("current") and quote.get("prev_close") else 0,
        "percent": ((quote.get("current") - quote.get("prev_close")) / quote.get("prev_close") * 100) if quote.get("current") and quote.get("prev_close") else 0,
        "after_hours": None,
        "open": quote.get("open"),
        "high": quote.get("high"),
        "low": quote.get("low"),
        "prev_close": quote.get("prev_close"),
        "volume": quote.get("volume"), 
        "market_cap": overview.get("MarketCapitalization"),
        "chart": chart
    }
    
    print(f">>> [DASHBOARD] Data consolidated for {symbol}, chart points: {len(chart)}", flush=True)
    return result


@tool
def predict_stock_signal(symbol: str):
    """
    Generate a BUY/SELL/HOLD trading signal using simple technical analysis.
    
    This tool analyzes stock price data (opening, closing, current) alongside
    basic technical indicators (moving averages, RSI, MACD) to generate a
    simple trading recommendation.
    
    Use this tool when:
    - The user asks whether to buy, sell, or hold a stock
    - The user wants a technical analysis based on price trends
    - The user wants a trading signal for decision making
    
    Args:
        symbol: Stock ticker symbol (e.g., AAPL, MSFT, TSLA)
    
    Returns:
        Dictionary containing:
        - symbol: The analyzed ticker
        - signal: Trading signal (BUY, SELL, or HOLD)
        - confidence: Confidence in the signal (0-100%)
        - reasoning: Explanation of indicators used
        - indicators: Dict of calculated indicators (SMA20, SMA50, RSI, MACD)
        - current_price: Current/latest price
        - price_change: Price change percentage
    """
    import pandas as pd
    
    try:
        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&outputsize=full&apikey={ALPHA_KEY}"
        response = requests.get(url)
        data = response.json()
        
        if "Error Message" in data or "Information" in data:
            return {
                "symbol": symbol,
                "signal": "HOLD",
                "confidence": 0,
                "reasoning": "Unable to fetch stock data. Please check ticker symbol.",
                "indicators": {},
                "error": str(data.get("Error Message") or data.get("Information"))
            }
        
        time_series = data.get("Time Series (Daily)", {})
        if not time_series:
            return {
                "symbol": symbol,
                "signal": "HOLD",
                "confidence": 0,
                "reasoning": "No price data available.",
                "indicators": {}
            }
        
        dates = sorted(time_series.keys(), reverse=True)[:100]
        prices = []
        closes_only = []
        
        for date in reversed(dates):
            prices.append({
                "date": date,
                "close": float(time_series[date]["4. close"]),
                "open": float(time_series[date]["1. open"]),
                "high": float(time_series[date]["2. high"]),
                "low": float(time_series[date]["3. low"])
            })
            closes_only.append(float(time_series[date]["4. close"]))
        
        df = pd.DataFrame(prices)
        
        sma_20 = df["close"].iloc[-20:].mean() if len(df) >= 20 else df["close"].mean()
        sma_50 = df["close"].iloc[-50:].mean() if len(df) >= 50 else df["close"].mean()

        closes = df["close"].values
        deltas = pd.Series(closes).diff()
        gains = (deltas.where(deltas > 0, 0)).rolling(window=14).mean()
        losses = (-deltas.where(deltas < 0, 0)).rolling(window=14).mean()
        rs = gains / losses
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1] if len(rsi) > 0 else 50
        
        ema_12 = df["close"].ewm(span=12, adjust=False).mean()
        ema_26 = df["close"].ewm(span=26, adjust=False).mean()
        macd_line = ema_12 - ema_26
        macd_signal = macd_line.ewm(span=9, adjust=False).mean()
        macd_diff = macd_line - macd_signal
        current_macd = macd_diff.iloc[-1] if len(macd_diff) > 0 else 0
        
        current_price = closes[-1]
        price_change = ((current_price - closes[0]) / closes[0]) * 100
        
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
            "symbol": symbol,
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
    
    except Exception as e:
        return {
            "symbol": symbol,
            "signal": "HOLD",
            "confidence": "0%",
            "reasoning": f"Error analyzing stock: {str(e)}",
            "indicators": {},
            "error": str(e)
        }

@tool
def get_broker_account():
    """
    Get the current Alpaca trading account information.

    Use this tool when:
    - The user asks about their trading account balance
    - The user wants to know their buying power or cash available
    - Before placing a trade, to check if there's enough buying power

    Returns:
        Dictionary containing:
        - cash: Available cash in the account
        - buying_power: Total buying power (cash + margin)
        - equity: Total account equity
        - portfolio_value: Current portfolio market value
        - status: Account status (ACTIVE, etc.)
        - paper: Whether this is paper trading (true/false)
    """
    from backend.trading.broker import get_account_info
    return get_account_info()


@tool
def get_broker_positions():
    """
    Get all current open positions from the Alpaca broker.

    Use this tool when:
    - The user asks what stocks they currently hold
    - The user wants to see their portfolio
    - Before suggesting a trade, to check existing positions
    - The user asks about unrealized profit/loss

    Returns:
        List of position dictionaries, each containing:
        - symbol: Stock ticker
        - qty: Number of shares held
        - market_value: Current market value
        - avg_entry_price: Average price paid per share
        - current_price: Current market price
        - unrealized_pl: Unrealized profit/loss in dollars
        - unrealized_pl_pct: Unrealized P&L as a percentage
    """
    from backend.trading.broker import get_positions
    return get_positions()


@tool
def place_trade(symbol: str, qty: int, side: str, order_type: str = "market"):
    """
    Place a trade order via the Alpaca broker.

    IMPORTANT: This executes a real trade (or paper trade if in sandbox mode).
    Always confirm the signal and reasoning with the user before calling this.

    Use this tool when:
    - The user explicitly asks to buy or sell a stock
    - The agent has analyzed patterns and the user confirms a trade
    - The user says "execute the trade" or "place the order"

    Safety limits enforced:
    - Maximum 100 shares per order
    - Maximum $10,000 per order
    - Paper trading by default

    Args:
        symbol: Stock ticker symbol (e.g., AAPL, MSFT)
        qty: Number of shares to buy or sell (max 100)
        side: "buy" or "sell"
        order_type: "market" (default) or "limit"

    Returns:
        Dictionary with order confirmation:
        - order_id: Unique order ID
        - status: Order status (new, filled, etc.)
        - symbol: Stock ticker
        - qty: Shares ordered
        - side: buy or sell
    """
    from backend.trading.broker import place_order
    return place_order(
        symbol=symbol,
        qty=qty,
        side=side,
        order_type=order_type,
    )


@tool
def close_trade(symbol: str):
    """
    Close an entire open position for a given stock symbol.

    This sells all shares of a long position (or covers a short position)
    at market price. Use this when the user wants to exit a position completely.

    Use this tool when:
    - The user says "close my position in AAPL"
    - The user says "sell all my shares of MSFT"
    - The agent detects a strong reversal pattern on a held position

    Args:
        symbol: Stock ticker to close the position for

    Returns:
        Dictionary with close order confirmation or error message.
    """
    from backend.trading.broker import close_position
    return close_position(symbol)
