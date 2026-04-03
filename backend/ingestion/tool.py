import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun

load_dotenv()

FINNHUB_KEY = os.getenv("FINNHUB_API_KEY")
ALPHA_KEY = os.getenv("ALPHAADVANTAGE_API_KEY")


# ---------------- FINNHUB ---------------- #

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


# ---------------- SEARCH ---------------- #

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


# ---------------- ALPHAVANTAGE ---------------- #

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
def get_gold_silver_price():
    """
    Retrieve current gold and silver spot prices.

    Use this tool for commodity and macro hedge tracking.

    Returns:
        Gold and silver spot price dataset.
    """
    return requests.get(
        f"https://www.alphavantage.co/query?function=GOLD_SILVER_SPOT&apikey={ALPHA_KEY}"
    ).json()
@tool
def get_stock_intraday_chart(symbol: str):
    """
    Retrieve intraday price series (5-minute interval) for charting.

    Use this tool when the agent needs granular price history for
    the current trading session.

    Args:
        symbol: Stock ticker
    """
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={symbol}&interval=5min&outputsize=small&apikey={ALPHA_KEY}"
    data = requests.get(url).json()
    
    time_series = data.get("Time Series (5min)", {})
    chart_data = []
    
    # Get last 50 data points and reverse to chronological order
    for timestamp in sorted(time_series.keys())[-50:]:
        chart_data.append({
            "time": timestamp.split(" ")[1][:5], # HH:MM
            "price": float(time_series[timestamp]["1. open"])
        })
    
    return chart_data


def fetch_stock_dashboard_data(symbol: str):
    """
    Directly fetches aggregated data for the dashboard widget.
    Bypasses LLM for performance and quota management.
    """
    print(f">>> [DASHBOARD] Consolidating data for {symbol}...", flush=True)
    
    # We use .invoke manually here for direct execution
    try:
        quote = get_stock_price.invoke({"symbol": symbol})
    except:
        quote = {}
        
    try:
        chart = get_stock_intraday_chart.invoke({"symbol": symbol})
    except:
        chart = []
        
    try:
        overview = company_overview.invoke({"symbol": symbol})
    except:
        overview = {}

    return {
        "symbol": symbol,
        "company": overview.get("name", symbol),
        "price": quote.get("current"),
        "change": quote.get("current") - quote.get("prev_close") if quote.get("current") and quote.get("prev_close") else 0,
        "percent": ((quote.get("current") - quote.get("prev_close")) / quote.get("prev_close") * 100) if quote.get("current") and quote.get("prev_close") else 0,
        "after_hours": None,
        "open": quote.get("open"),
        "high": quote.get("high"),
        "low": quote.get("low"),
        "prev_close": quote.get("prev_close"),
        "volume": quote.get("volume"), 
        "market_cap": overview.get("market_cap"),
        "chart": chart
    }


# =============================================================================
# NEW: CHART PATTERN DETECTION TOOLS
# =============================================================================
# These tools integrate the foduucom/stockmarket-pattern-detection-yolov8 model
# from HuggingFace. The model detects chart patterns (Head & Shoulders, 
# Double Top/Bottom, Triangle, etc.) and generates BUY/SELL/HOLD signals.
# =============================================================================

@tool
def detect_chart_patterns(symbol: str):
    """
    Run YOLOv8 AI pattern detection on a stock's candlestick chart.

    This tool generates a candlestick chart image from the stock's recent
    price history, then runs the foduucom/stockmarket-pattern-detection-yolov8
    model to detect technical chart patterns. It returns detected patterns
    along with a BUY/SELL/HOLD trading signal.

    Use this tool when:
    - The user asks about chart patterns for a stock
    - The user wants a technical analysis based on visual patterns
    - The user asks whether to buy, sell, or hold a stock
    - The user wants pattern-based trading signals

    Detectable patterns: Head & Shoulders (top/bottom), Double Top (M_Head),
    Double Bottom (W_Bottom), Triangle, StockLine (trend line).

    Args:
        symbol: Stock ticker symbol (e.g., AAPL, MSFT, TSLA)

    Returns:
        Dictionary containing:
        - symbol: The analyzed ticker
        - patterns: List of detected patterns with confidence scores
        - signal: Trading signal (BUY, SELL, or HOLD)
        - signal_confidence: Confidence in the signal (0-100%)
        - reasoning: Explanation of why this signal was generated
    """
    from backend.pattern_detection.pattern_detector import analyze_chart
    from backend.trading.signal_engine import generate_signal

    # Step 1: Run the YOLOv8 pattern detection pipeline
    analysis = analyze_chart(symbol, period="3mo")

    if analysis.error:
        return {
            "symbol": symbol,
            "error": analysis.error,
            "patterns": [],
            "signal": "HOLD",
            "signal_confidence": 0,
            "reasoning": f"Pattern detection failed: {analysis.error}",
        }

    # Step 2: Convert detected patterns to a trading signal
    signal = generate_signal(analysis.patterns)

    return {
        "symbol": analysis.symbol,
        "patterns": [
            {
                "name": p.name,
                "confidence": f"{p.confidence:.1%}",
                "confidence_raw": p.confidence,
            }
            for p in analysis.patterns
        ],
        "signal": signal.signal,
        "signal_confidence": f"{signal.confidence:.1%}",
        "score": signal.score,
        "reasoning": signal.reasoning,
        "individual_signals": signal.individual_signals,
        "chart_image": analysis.chart_image_path,
        "timestamp": analysis.analysis_timestamp,
    }


# =============================================================================
# NEW: BROKER / TRADING TOOLS (Alpaca Markets API)
# =============================================================================
# These tools connect to the Alpaca Markets brokerage API to execute real
# trades. By default, they use PAPER TRADING (sandbox) so no real money
# is at risk. Configure via ALPACA_API_KEY and ALPACA_SECRET_KEY in .env.
# =============================================================================

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
