"""YOLO-based stock chart pattern detection pipeline."""

import matplotlib
matplotlib.use("Agg")
import os
import tempfile
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class DetectedPattern:
    """
    Represents a single pattern detected by the YOLOv8 model.
    
    Attributes:
        name: Human-readable pattern name (e.g., "Head and shoulders top")
        confidence: Model's confidence score (0.0 to 1.0)
        bbox: Bounding box coordinates [x1, y1, x2, y2] on the chart image
    """
    name: str
    confidence: float
    bbox: List[float] = field(default_factory=list)


@dataclass
class ChartAnalysis:
    """
    Complete analysis result from the pattern detection pipeline.
    
    Attributes:
        symbol: Stock ticker that was analyzed
        patterns: List of detected patterns with confidence scores
        chart_image_path: Path to the generated candlestick chart image
        analysis_timestamp: When the analysis was performed
        error: Error message if analysis failed, None if successful
    """
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
    """
    Lazy-loads the YOLOv8 model from HuggingFace Hub.
    
    The model is downloaded and cached locally on first run (~25MB).
    Subsequent calls return the cached model instance immediately.
    
    Returns:
        YOLO model instance ready for inference
    
    Raises:
        ImportError: If ultralytics is not installed
        Exception: If model download/load fails
    """
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
            logger.info(f"[PATTERN] Model weights downloaded to: {model_path}")
            _model = YOLO(model_path)

            _model.overrides['conf'] = 0.25
            _model.overrides['iou'] = 0.45
            
            logger.info("[PATTERN] Model loaded successfully!")
            
        except ImportError:
            logger.error("[PATTERN] ultralytics not installed! Run: pip install ultralytics")
            raise
        except Exception as e:
            logger.error(f"[PATTERN] Failed to load model: {e}")
            raise
    
    return _model


def generate_chart_image(symbol: str, period: str = "3mo") -> str:
    """
    Fetches OHLCV data and generates a candlestick chart image.
    
    This function:
    1. Downloads historical price data from Yahoo Finance
    2. Generates a professional candlestick chart using mplfinance
    3. Saves it as a PNG image in a temp directory
    
    The generated chart mimics what a trader would see on their screen,
    which is what the YOLOv8 model was trained on.
    
    Args:
        symbol: Stock ticker (e.g., "AAPL", "MSFT", "TSLA")
        period: Data period — "1mo", "3mo", "6mo", "1y"
                Default "3mo" gives enough data points for pattern detection
    
    Returns:
        Absolute path to the generated PNG chart image
    
    Raises:
        ValueError: If no price data found for the symbol
        ImportError: If yfinance or mplfinance not installed
    """
    import yfinance as yf
    import mplfinance as mpf
    
    logger.info(f"[PATTERN] Fetching {period} of OHLCV data for {symbol}...")
    
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period)
    
    if df.empty:
        raise ValueError(f"No price data found for symbol: {symbol}")
    
    logger.info(f"[PATTERN] Got {len(df)} data points for {symbol}")
    
    charts_dir = os.path.join(tempfile.gettempdir(), "stock_charts")
    os.makedirs(charts_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    chart_path = os.path.join(charts_dir, f"{symbol}_{timestamp}.png")

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
    
    logger.info(f"[PATTERN] Chart saved to: {chart_path}")
    return chart_path


def detect_patterns(image_path: str) -> List[DetectedPattern]:
    """
    Runs YOLOv8 inference on a candlestick chart image.
    
    The model scans the image for the 6 supported pattern types and
    returns each detection with its confidence score and bounding box.
    
    Args:
        image_path: Absolute path to a candlestick chart PNG image
    
    Returns:
        List of DetectedPattern objects sorted by confidence (highest first).
        Empty list if no patterns detected.
    
    Example return:
        [
            DetectedPattern(name="Head and shoulders top", confidence=0.82, bbox=[100, 50, 400, 300]),
            DetectedPattern(name="Triangle", confidence=0.45, bbox=[200, 100, 500, 350]),
        ]
    """
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

                if 0 <= cls_idx < len(PATTERN_CLASSES):
                    pattern_name = PATTERN_CLASSES[cls_idx]
                else:
                    pattern_name = f"Unknown_Class_{cls_idx}"
                
                detected.append(DetectedPattern(
                    name=pattern_name,
                    confidence=round(conf, 4),
                    bbox=[round(b, 2) for b in bbox],
                ))
                
                logger.info(
                    f"[PATTERN] Detected: {pattern_name} "
                    f"(confidence: {conf:.2%})"
                )

    detected.sort(key=lambda p: p.confidence, reverse=True)
    
    if not detected:
        logger.info("[PATTERN] No patterns detected in this chart.")
    
    return detected


def analyze_chart(symbol: str, period: str = "3mo") -> ChartAnalysis:
    """
    Complete chart pattern analysis pipeline for a stock symbol.
    
    This is the main entry point used by the LangChain tool. It:
    1. Fetches OHLCV data from Yahoo Finance
    2. Generates a candlestick chart image
    3. Runs YOLOv8 pattern detection
    4. Returns structured results
    
    Args:
        symbol: Stock ticker (e.g., "AAPL")
        period: Historical data period ("1mo", "3mo", "6mo", "1y")
    
    Returns:
        ChartAnalysis object with patterns, image path, and metadata.
        If an error occurs, ChartAnalysis.error will contain the message.
    
    Example:
        >>> result = analyze_chart("AAPL")
        >>> for p in result.patterns:
        ...     print(f"{p.name}: {p.confidence:.2%}")
        Head and shoulders top: 82.15%
        Triangle: 45.30%
    """
    logger.info(f"[PATTERN] Starting full analysis for {symbol}...")
    
    try:
        chart_path = generate_chart_image(symbol, period)

        patterns = detect_patterns(chart_path)

        return ChartAnalysis(
            symbol=symbol.upper(),
            patterns=patterns,
            chart_image_path=chart_path,
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
