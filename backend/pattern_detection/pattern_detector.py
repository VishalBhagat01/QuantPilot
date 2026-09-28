"""YOLO-based stock chart pattern detection pipeline."""

import logging
import os
from typing import List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from backend.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class DetectedPattern:
    """Represents a single pattern detected by the YOLOv8 model."""
    name: str
    confidence: float
    bbox: List[float] = field(default_factory=list)


@dataclass
class ChartAnalysis:
    """Complete analysis result from the pattern detection pipeline."""
    symbol: str
    patterns: List[DetectedPattern]
    chart_image_path: Optional[str] = None
    analysis_timestamp: str = ""
    error: Optional[str] = None


PATTERN_CLASSES = [
    'Head and shoulders bottom',
    'Head and shoulders top',
    'M_Head',
    'StockLine',
    'Triangle',
    'W_Bottom',
]

_model = None


def _get_model():
    """Lazy-loads the YOLOv8 model from HuggingFace Hub with local caching."""
    global _model

    if _model is None:
        logger.info("[PATTERN] Loading YOLOv8 model from HuggingFace...")
        try:
            from ultralytics import YOLO
            from huggingface_hub import hf_hub_download

            model_path = hf_hub_download(
                repo_id="foduucom/stockmarket-pattern-detection-yolov8",
                filename="model.pt"
            )
            logger.info(f"[PATTERN] Model weights located at: {model_path}")
            _model = YOLO(model_path)
            _model.overrides['conf'] = 0.25
            _model.overrides['iou'] = 0.45
            logger.info("[PATTERN] Model loaded successfully.")
        except ImportError:
            logger.error("[PATTERN] ultralytics not installed. Run: pip install ultralytics")
            raise
        except Exception as e:
            logger.error(f"[PATTERN] Failed to load YOLOv8 model: {e}")
            raise

    return _model


def generate_chart_image(symbol: str, period: str = "3mo") -> str:
    """Fetches OHLCV data and generates a candlestick chart image in managed temp storage."""
    import yfinance as yf
    import mplfinance as mpf

    logger.info(f"[PATTERN] Fetching {period} of OHLCV data for {symbol}...")
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period)

    if df.empty:
        raise ValueError(f"No price data found for symbol: {symbol}")

    charts_dir = settings.temp_dir / "stock_charts"
    charts_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    chart_path = str(charts_dir / f"{symbol}_{timestamp}.png")

    try:
        mpf.plot(
            df,
            type='candle',
            style='charles',
            volume=True,
            mav=(10, 20),
            title=f'{symbol} - Pattern Analysis',
            figsize=(12, 8),
            savefig=chart_path,
        )
    finally:
        plt.close('all')

    logger.info(f"[PATTERN] Chart saved to: {chart_path}")
    return chart_path


def detect_patterns(image_path: str) -> List[DetectedPattern]:
    """Runs YOLOv8 inference on a candlestick chart image."""
    model = _get_model()
    logger.info(f"[PATTERN] Running inference on: {image_path}")

    results = model.predict(image_path, save=False, verbose=False)
    detected = []

    if results and len(results) > 0:
        result = results[0]
        if result.boxes and len(result.boxes) > 0:
            class_indices = result.boxes.cls.tolist()
            confidences = result.boxes.conf.tolist()
            bboxes = result.boxes.xyxy.tolist()

            for cls_idx, conf, bbox in zip(class_indices, confidences, bboxes):
                cls_idx = int(cls_idx)
                pattern_name = PATTERN_CLASSES[cls_idx] if 0 <= cls_idx < len(PATTERN_CLASSES) else f"Unknown_Class_{cls_idx}"
                detected.append(DetectedPattern(
                    name=pattern_name,
                    confidence=round(conf, 4),
                    bbox=[round(b, 2) for b in bbox],
                ))

    detected.sort(key=lambda p: p.confidence, reverse=True)
    return detected


def analyze_chart(symbol: str, period: str = "3mo", cleanup_image: bool = True) -> ChartAnalysis:
    """
    Complete chart pattern analysis pipeline for a stock symbol.
    Cleans up the temporary chart image after inference to prevent disk accumulation.
    """
    logger.info(f"[PATTERN] Starting full analysis for {symbol}...")
    chart_path = None

    try:
        chart_path = generate_chart_image(symbol, period)
        patterns = detect_patterns(chart_path)

        return ChartAnalysis(
            symbol=symbol.upper(),
            patterns=patterns,
            chart_image_path=chart_path if not cleanup_image else None,
            analysis_timestamp=datetime.now().isoformat(),
            error=None,
        )
    except Exception as e:
        logger.error(f"[PATTERN] Analysis failed for {symbol}: {e}")
        return ChartAnalysis(
            symbol=symbol.upper(),
            patterns=[],
            chart_image_path=None,
            analysis_timestamp=datetime.now().isoformat(),
            error=str(e),
        )
    finally:
        if cleanup_image and chart_path and os.path.exists(chart_path):
            try:
                os.remove(chart_path)
            except OSError:
                pass
