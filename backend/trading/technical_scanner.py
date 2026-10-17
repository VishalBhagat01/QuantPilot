"""Local, model-free market scanning with OHLCV indicators."""

from dataclasses import dataclass
from typing import Iterable, List, Optional

import pandas as pd


DEFAULT_SYMBOLS = (
    "AAPL",
    "MSFT",
    "NVDA",
    "AMZN",
    "META",
    "TSLA",
    "GOOGL",
    "AMD",
    "SPY",
)

BUY_THRESHOLD = 5
SELL_THRESHOLD = -5
MINIMUM_ROWS = 55


@dataclass(frozen=True)
class ScanResult:
    """Explainable technical scan result for one symbol."""

    symbol: str
    signal: str
    score: int
    confidence: int
    current_price: float
    indicators: dict
    reasons: List[str]
    error: Optional[str] = None

    def as_dict(self) -> dict:
        """Return the API-safe representation of this result."""
        reasoning = self.error or (
            " | ".join(self.reasons) if self.reasons else "No strong technical signal."
        )
        return {
            "symbol": self.symbol,
            "signal": self.signal,
            "score": self.score,
            "confidence": f"{self.confidence}%",
            "confidence_raw": self.confidence,
            "signal_confidence": self.confidence,
            "current_price": round(self.current_price, 2),
            "indicators": self.indicators,
            "reasons": self.reasons,
            "reasoning": reasoning,
            "error": self.error,
        }


def _normalise_ohlcv(data: pd.DataFrame) -> pd.DataFrame:
    """Normalise yfinance output, including its optional MultiIndex columns."""
    if data.empty:
        return pd.DataFrame()

    frame = data.copy()
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(0)

    required = ("Open", "High", "Low", "Close", "Volume")
    if not set(required).issubset(frame.columns):
        return pd.DataFrame()

    return frame[list(required)].apply(pd.to_numeric, errors="coerce").dropna()


def fetch_ohlcv(symbol: str, period: str = "6mo") -> pd.DataFrame:
    """Fetch daily OHLCV data using yfinance."""
    import yfinance as yf

    data = yf.download(
        symbol,
        period=period,
        interval="1d",
        progress=False,
        auto_adjust=False,
        threads=False,
    )
    return _normalise_ohlcv(data)


def _rsi(close: pd.Series, period: int = 14) -> float:
    delta = close.diff()
    gains = delta.clip(lower=0).rolling(period).mean()
    losses = -delta.clip(upper=0).rolling(period).mean()
    relative_strength = gains / losses.replace(0, 1e-9)
    value = 100 - (100 / (1 + relative_strength.iloc[-1]))
    return float(value) if pd.notna(value) else 50.0


def _build_scan(symbol: str, data: pd.DataFrame) -> ScanResult:
    close = data["Close"]
    volume = data["Volume"]
    current_price = float(close.iloc[-1])
    sma_20 = float(close.rolling(20).mean().iloc[-1])
    sma_50 = float(close.rolling(50).mean().iloc[-1])
    ema_12 = close.ewm(span=12, adjust=False).mean()
    ema_26 = close.ewm(span=26, adjust=False).mean()
    macd = ema_12 - ema_26
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    macd_histogram = float((macd - macd_signal).iloc[-1])
    rsi = _rsi(close)
    average_volume = float(volume.rolling(20).mean().iloc[-1])
    volume_ratio = float(volume.iloc[-1] / average_volume) if average_volume else 0.0
    high_20 = float(close.iloc[-21:-1].max())
    low_20 = float(close.iloc[-21:-1].min())

    score = 0
    reasons: List[str] = []

    if current_price > sma_20 > sma_50:
        score += 2
        reasons.append("Price is above a bullish SMA20/SMA50 trend")
    elif current_price < sma_20 < sma_50:
        score -= 2
        reasons.append("Price is below a bearish SMA20/SMA50 trend")
    elif current_price > sma_20:
        score += 1
        reasons.append("Price is above SMA20")
    else:
        score -= 1
        reasons.append("Price is below SMA20")

    if 50 <= rsi <= 70:
        score += 2
        reasons.append(f"RSI has healthy bullish momentum ({rsi:.1f})")
    elif rsi < 30:
        score += 1
        reasons.append(f"RSI is oversold ({rsi:.1f})")
    elif rsi > 70:
        score -= 1
        reasons.append(f"RSI is overbought ({rsi:.1f})")
    else:
        reasons.append(f"RSI is neutral ({rsi:.1f})")

    if macd_histogram > 0:
        score += 2
        reasons.append("MACD histogram is positive")
    else:
        score -= 2
        reasons.append("MACD histogram is negative")

    if volume_ratio >= 1.5:
        score += 1 if close.iloc[-1] >= close.iloc[-2] else -1
        reasons.append(f"Volume is {volume_ratio:.1f}x its 20-day average")

    if current_price > high_20:
        score += 2
        reasons.append("Price broke above the 20-day high")
    elif current_price < low_20:
        score -= 2
        reasons.append("Price broke below the 20-day low")

    if score >= BUY_THRESHOLD:
        signal = "BUY"
    elif score <= SELL_THRESHOLD:
        signal = "SELL"
    else:
        signal = "HOLD"

    confidence = min(95, 50 + abs(score) * 7)
    indicators = {
        "SMA_20": f"${sma_20:.2f}",
        "SMA_50": f"${sma_50:.2f}",
        "RSI_14": f"{rsi:.1f}",
        "MACD_histogram": f"{macd_histogram:.4f}",
        "volume_ratio": f"{volume_ratio:.2f}x",
        "high_20": f"${high_20:.2f}",
        "low_20": f"${low_20:.2f}",
        "current_price": f"${current_price:.2f}",
    }
    return ScanResult(
        symbol=symbol,
        signal=signal,
        score=score,
        confidence=confidence,
        current_price=current_price,
        indicators=indicators,
        reasons=reasons,
    )


def scan_symbol(symbol: str, data: Optional[pd.DataFrame] = None) -> ScanResult:
    """Scan one ticker using deterministic technical rules."""
    clean_symbol = symbol.strip().upper()
    if not clean_symbol:
        raise ValueError("Ticker symbol cannot be empty")

    try:
        frame = _normalise_ohlcv(data) if data is not None else fetch_ohlcv(clean_symbol)
        if len(frame) < MINIMUM_ROWS:
            return ScanResult(
                symbol=clean_symbol,
                signal="HOLD",
                score=0,
                confidence=0,
                current_price=float(frame["Close"].iloc[-1]) if not frame.empty else 0.0,
                indicators={},
                reasons=[],
                error=f"Insufficient historical data for {clean_symbol}; need at least {MINIMUM_ROWS} trading days.",
            )
        return _build_scan(clean_symbol, frame)
    except Exception as exc:
        return ScanResult(
            symbol=clean_symbol,
            signal="HOLD",
            score=0,
            confidence=0,
            current_price=0.0,
            indicators={},
            reasons=[],
            error=f"Unable to scan {clean_symbol}: {exc}",
        )


def scan_market(symbols: Optional[Iterable[str]] = None) -> List[dict]:
    """Scan a ticker universe and rank successful results by score."""
    clean_symbols = list(symbols or DEFAULT_SYMBOLS)
    results = [scan_symbol(symbol) for symbol in clean_symbols]
    return [
        result.as_dict()
        for result in sorted(results, key=lambda item: item.score, reverse=True)
    ]
