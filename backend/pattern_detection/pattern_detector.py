# =============================================================================
# pattern_detector.py — YOLOv8 Stock Market Pattern Detection Engine
# =============================================================================
#
# PURPOSE:
#   This module generates candlestick chart images from real stock price data
#   and runs the foduucom/stockmarket-pattern-detection-yolov8 model to detect
#   chart patterns. Detected patterns are returned with confidence scores.
#
# HOW IT WORKS:
#   1. Fetches OHLCV data using yfinance (last 3 months of daily data)
#   2. Generates a candlestick chart image using mplfinance
#   3. Runs YOLOv8 inference on the generated chart image
#   4. Returns detected patterns with bounding boxes and confidence scores
#
# SUPPORTED PATTERNS (from the YOLOv8 model):
#   - Head and shoulders bottom → Bullish reversal signal
#   - Head and shoulders top    → Bearish reversal signal
#   - M_Head (Double Top)       → Bearish reversal signal
#   - W_Bottom (Double Bottom)  → Bullish reversal signal
#   - Triangle                  → Continuation / breakout pending
#   - StockLine                 → Trend line (neutral)
#
# DEPENDENCIES:
#   pip install ultralytics yfinance mplfinance opencv-python Pillow
#
# =============================================================================

import os
import tempfile
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime

# Setup logging for this module
logger = logging.getLogger(__name__)

# =============================================================================
# DATA CLASSES — Structured output for pattern detection results
# =============================================================================

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


# =============================================================================
# PATTERN LABEL MAPPING — Maps model class indices to human-readable names
# =============================================================================
# These labels come directly from the YOLOv8 model's training configuration.
# The model was trained to detect exactly these 6 pattern classes.
# =============================================================================

PATTERN_CLASSES = [
    'Head and shoulders bottom',  # Class 0 — Bullish reversal
    'Head and shoulders top',     # Class 1 — Bearish reversal
    'M_Head',                     # Class 2 — Double Top (Bearish)
    'StockLine',                  # Class 3 — Trend line (Neutral)
    'Triangle',                   # Class 4 — Continuation pattern
    'W_Bottom',                   # Class 5 — Double Bottom (Bullish)
]


# =============================================================================
# GLOBAL MODEL CACHE — Load the model once and reuse across requests
# =============================================================================
# Loading a YOLO model from HuggingFace takes ~5-10 seconds.
# We cache it globally so subsequent predictions are instant (~100ms).
# =============================================================================

_model = None  # Will be loaded on first use (lazy initialization)


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
            
            # ---------------------------------------------------------------
            # Download the best.pt weights from HuggingFace Hub.
            # hf_hub_download caches the file locally (~25MB) so subsequent
            # calls are instant. Then we load it with the YOLO constructor.
            # ---------------------------------------------------------------
            model_path = hf_hub_download(
                repo_id="foduucom/stockmarket-pattern-detection-yolov8",
                filename="model.pt"
            )
            logger.info(f"[PATTERN] Model weights downloaded to: {model_path}")
            _model = YOLO(model_path)
            
            # ---------------------------------------------------------------
            # Configure inference parameters:
            #   conf=0.25 → Minimum confidence threshold (25%)
            #     Lower = more detections (more false positives)
            #     Higher = fewer detections (may miss real patterns)
            #   iou=0.45 → Non-Max Suppression IoU threshold
            #     Controls overlap handling for duplicate detections
            # ---------------------------------------------------------------
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


# =============================================================================
# CHART IMAGE GENERATION — Creates candlestick charts from price data
# =============================================================================

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
    
    # ---------------------------------------------------------------
    # Step 1: Fetch historical OHLCV data from Yahoo Finance
    # yfinance returns a pandas DataFrame with columns:
    #   Open, High, Low, Close, Volume, Dividends, Stock Splits
    # ---------------------------------------------------------------
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period)
    
    if df.empty:
        raise ValueError(f"No price data found for symbol: {symbol}")
    
    logger.info(f"[PATTERN] Got {len(df)} data points for {symbol}")
    
    # ---------------------------------------------------------------
    # Step 2: Generate candlestick chart image
    # We use a dark "nightclouds" style to match typical trading platforms.
    # The chart includes volume bars and moving averages for better
    # pattern context (the model was trained on similar looking charts).
    # ---------------------------------------------------------------
    
    # Create a temp directory for chart images (cleaned up periodically)
    charts_dir = os.path.join(tempfile.gettempdir(), "stock_charts")
    os.makedirs(charts_dir, exist_ok=True)
    
    # Unique filename per symbol + timestamp to avoid collisions
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    chart_path = os.path.join(charts_dir, f"{symbol}_{timestamp}.png")
    
    # ---------------------------------------------------------------
    # mplfinance configuration:
    #   type='candle'   → Candlestick chart (not line or OHLC bars)
    #   style='charles' → Classic trading chart colors (green/red)
    #   volume=True     → Show volume bars below the chart
    #   mav=(10, 20)    → 10-day and 20-day moving averages overlay
    #   figsize=(12, 8) → Large enough for YOLOv8 to detect patterns
    #   savefig=path    → Save directly to disk (no display needed)
    # ---------------------------------------------------------------
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


# =============================================================================
# PATTERN DETECTION — Runs YOLOv8 inference on chart images
# =============================================================================

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
    
    # ---------------------------------------------------------------
    # Run YOLOv8 prediction
    #   save=False → Don't save annotated images (we just need the data)
    #   verbose=False → Suppress console output from ultralytics
    # ---------------------------------------------------------------
    results = model.predict(image_path, save=False, verbose=False)
    
    detected = []
    
    if results and len(results) > 0:
        result = results[0]  # First (and only) image result
        
        if result.boxes and len(result.boxes) > 0:
            # ---------------------------------------------------------------
            # Extract detections from YOLOv8 output:
            #   result.boxes.cls   → Class indices (integers)
            #   result.boxes.conf  → Confidence scores (0.0 to 1.0)
            #   result.boxes.xyxy  → Bounding boxes [x1, y1, x2, y2]
            # ---------------------------------------------------------------
            class_indices = result.boxes.cls.tolist()
            confidences = result.boxes.conf.tolist()
            bboxes = result.boxes.xyxy.tolist()
            
            for cls_idx, conf, bbox in zip(class_indices, confidences, bboxes):
                cls_idx = int(cls_idx)
                
                # Map class index to pattern name (safety check for index)
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
    
    # Sort by confidence (highest first) — most reliable patterns first
    detected.sort(key=lambda p: p.confidence, reverse=True)
    
    if not detected:
        logger.info("[PATTERN] No patterns detected in this chart.")
    
    return detected


# =============================================================================
# FULL ANALYSIS PIPELINE — End-to-end: fetch → chart → detect → result
# =============================================================================

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
        # Step 1 + 2: Fetch data and generate chart image
        chart_path = generate_chart_image(symbol, period)
        
        # Step 3: Run pattern detection
        patterns = detect_patterns(chart_path)
        
        # Step 4: Package results
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
