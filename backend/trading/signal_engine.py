# =============================================================================
# signal_engine.py — Trading Signal Generator
# =============================================================================
#
# PURPOSE:
#   Converts detected chart patterns from YOLOv8 into actionable trading
#   signals (BUY / SELL / HOLD) with a confidence-weighted scoring system.
#
# HOW THE SCORING WORKS:
#   Each pattern has a predefined signal direction and weight:
#     - Bullish patterns (W_Bottom, H&S Bottom) → positive score
#     - Bearish patterns (M_Head, H&S Top) → negative score
#     - Neutral patterns (Triangle, StockLine) → near-zero score
#
#   The final signal is determined by the weighted average of all detected
#   patterns, adjusted by their confidence scores. This prevents a single
#   low-confidence detection from triggering a trade.
#
# SIGNAL THRESHOLDS:
#   score > +0.3  → BUY signal
#   score < -0.3  → SELL signal
#   otherwise     → HOLD signal
#
# =============================================================================

import logging
from typing import List, Optional
from dataclasses import dataclass, field
from pattern_detection.pattern_detector import DetectedPattern

logger = logging.getLogger(__name__)


# =============================================================================
# PATTERN → SIGNAL MAPPING
# =============================================================================
# Each pattern is mapped to:
#   direction: "bullish", "bearish", or "neutral"
#   weight: How strongly this pattern signals a trade (0.0 to 1.0)
#   description: Human-readable explanation for the agent/user
#
# These mappings are based on classical technical analysis theory.
# Weights are conservative to avoid overconfidence in a single pattern.
# =============================================================================

PATTERN_SIGNAL_MAP = {
    # ---------------------------------------------------------------
    # BULLISH PATTERNS — Indicate a potential price increase
    # ---------------------------------------------------------------
    'Head and shoulders bottom': {
        'direction': 'bullish',
        'weight': 0.85,       # Strong bullish — reliable reversal pattern
        'signal': 'BUY',
        'description': (
            'Inverse Head & Shoulders detected — one of the most reliable '
            'bullish reversal patterns. Price is likely to break upward.'
        ),
    },
    'W_Bottom': {
        'direction': 'bullish',
        'weight': 0.75,       # Strong bullish — double bottom support
        'signal': 'BUY',
        'description': (
            'Double Bottom (W pattern) detected — price tested support '
            'twice and bounced. Indicates strong buying pressure.'
        ),
    },
    
    # ---------------------------------------------------------------
    # BEARISH PATTERNS — Indicate a potential price decrease
    # ---------------------------------------------------------------
    'Head and shoulders top': {
        'direction': 'bearish',
        'weight': 0.85,       # Strong bearish — reliable reversal pattern
        'signal': 'SELL',
        'description': (
            'Head & Shoulders Top detected — one of the most reliable '
            'bearish reversal patterns. Price is likely to break downward.'
        ),
    },
    'M_Head': {
        'direction': 'bearish',
        'weight': 0.75,       # Strong bearish — double top resistance
        'signal': 'SELL',
        'description': (
            'Double Top (M pattern) detected — price tested resistance '
            'twice and rejected. Indicates strong selling pressure.'
        ),
    },
    
    # ---------------------------------------------------------------
    # NEUTRAL PATTERNS — Wait for breakout direction
    # ---------------------------------------------------------------
    'Triangle': {
        'direction': 'neutral',
        'weight': 0.40,       # Moderate — needs breakout confirmation
        'signal': 'HOLD',
        'description': (
            'Triangle pattern detected — price is consolidating. '
            'Wait for a breakout above or below the triangle for direction.'
        ),
    },
    'StockLine': {
        'direction': 'neutral',
        'weight': 0.20,       # Weak — just a trend line
        'signal': 'HOLD',
        'description': (
            'Stock trend line detected — indicates ongoing trend but '
            'no reversal signal. Current position should be maintained.'
        ),
    },
}


# =============================================================================
# DATA CLASSES — Structured signal output
# =============================================================================

@dataclass
class TradingSignal:
    """
    Final trading signal generated from pattern analysis.
    
    Attributes:
        signal: "BUY", "SELL", or "HOLD"
        confidence: Overall signal confidence (0.0 to 1.0)
        score: Raw weighted score (-1.0 to +1.0, positive=bullish)
        patterns_detected: List of pattern names that contributed
        reasoning: Human-readable explanation of why this signal was generated
        individual_signals: Breakdown of each pattern's contribution
    """
    signal: str                            # "BUY", "SELL", or "HOLD"
    confidence: float                      # 0.0 to 1.0
    score: float                           # -1.0 to +1.0
    patterns_detected: List[str] = field(default_factory=list)
    reasoning: str = ""
    individual_signals: List[dict] = field(default_factory=list)


# =============================================================================
# SIGNAL THRESHOLDS — Controls how aggressive the signal generator is
# =============================================================================
# Adjust these if you want more/fewer trade signals:
#   Lower thresholds = more trades triggered (more aggressive)
#   Higher thresholds = fewer trades triggered (more conservative)
# =============================================================================

BUY_THRESHOLD = 0.3     # Weighted score above +0.3 → BUY
SELL_THRESHOLD = -0.3    # Weighted score below -0.3 → SELL
MIN_CONFIDENCE = 0.30    # Ignore patterns with confidence below 30%


# =============================================================================
# SIGNAL GENERATION — Core logic
# =============================================================================

def generate_signal(patterns: List[DetectedPattern]) -> TradingSignal:
    """
    Converts a list of detected patterns into a single trading signal.
    
    Algorithm:
    1. Filter out low-confidence detections (below MIN_CONFIDENCE)
    2. Look up each pattern's signal direction and weight
    3. Calculate a weighted score:
       - Bullish patterns contribute +weight * confidence
       - Bearish patterns contribute -weight * confidence
       - Neutral patterns contribute 0
    4. Average the score across all valid detections
    5. Map the final score to BUY/SELL/HOLD using thresholds
    
    Args:
        patterns: List of DetectedPattern objects from YOLOv8
    
    Returns:
        TradingSignal with the computed signal, confidence, and reasoning
    
    Example:
        >>> patterns = [
        ...     DetectedPattern(name="Head and shoulders top", confidence=0.82),
        ...     DetectedPattern(name="Triangle", confidence=0.45),
        ... ]
        >>> signal = generate_signal(patterns)
        >>> print(signal.signal)  # "SELL"
    """
    
    # ---------------------------------------------------------------
    # Step 1: Handle edge case — no patterns detected
    # ---------------------------------------------------------------
    if not patterns:
        return TradingSignal(
            signal="HOLD",
            confidence=0.0,
            score=0.0,
            patterns_detected=[],
            reasoning=(
                "No chart patterns were detected by the YOLOv8 model. "
                "This could mean the stock is in a ranging/choppy market "
                "with no clear pattern formation. Recommendation: HOLD "
                "current position and wait for clearer signals."
            ),
            individual_signals=[],
        )
    
    # ---------------------------------------------------------------
    # Step 2: Filter patterns by minimum confidence threshold
    # ---------------------------------------------------------------
    valid_patterns = [
        p for p in patterns 
        if p.confidence >= MIN_CONFIDENCE
    ]
    
    if not valid_patterns:
        return TradingSignal(
            signal="HOLD",
            confidence=0.0,
            score=0.0,
            patterns_detected=[p.name for p in patterns],
            reasoning=(
                f"Patterns were detected but all below the minimum confidence "
                f"threshold of {MIN_CONFIDENCE:.0%}. Detected: "
                f"{', '.join(p.name + f' ({p.confidence:.0%})' for p in patterns)}. "
                f"Recommendation: HOLD — insufficient confidence for a trade."
            ),
            individual_signals=[],
        )
    
    # ---------------------------------------------------------------
    # Step 3: Calculate weighted signal score
    # ---------------------------------------------------------------
    total_score = 0.0
    total_weight = 0.0
    individual_signals = []
    
    for pattern in valid_patterns:
        # Look up this pattern's signal configuration
        signal_config = PATTERN_SIGNAL_MAP.get(pattern.name)
        
        if signal_config is None:
            # Unknown pattern type — skip but log it
            logger.warning(f"[SIGNAL] Unknown pattern: {pattern.name}")
            continue
        
        # Calculate this pattern's contribution to the total score
        direction_multiplier = {
            'bullish': +1.0,   # Positive = buy pressure
            'bearish': -1.0,   # Negative = sell pressure
            'neutral':  0.0,   # Zero = no directional bias
        }.get(signal_config['direction'], 0.0)
        
        # Score = direction * weight * confidence
        # Example: H&S Top at 82% confidence = -1.0 * 0.85 * 0.82 = -0.697
        pattern_score = direction_multiplier * signal_config['weight'] * pattern.confidence
        
        total_score += pattern_score
        total_weight += signal_config['weight'] * pattern.confidence
        
        individual_signals.append({
            'pattern': pattern.name,
            'confidence': pattern.confidence,
            'direction': signal_config['direction'],
            'signal': signal_config['signal'],
            'weight': signal_config['weight'],
            'score_contribution': round(pattern_score, 4),
            'description': signal_config['description'],
        })
    
    # ---------------------------------------------------------------
    # Step 4: Average the score (normalized by total weight)
    # ---------------------------------------------------------------
    if total_weight > 0:
        avg_score = total_score / total_weight
    else:
        avg_score = 0.0
    
    # ---------------------------------------------------------------
    # Step 5: Map score to signal using thresholds
    # ---------------------------------------------------------------
    if avg_score > BUY_THRESHOLD:
        final_signal = "BUY"
    elif avg_score < SELL_THRESHOLD:
        final_signal = "SELL"
    else:
        final_signal = "HOLD"
    
    # Confidence = how strongly we believe in this signal (absolute score)
    signal_confidence = min(abs(avg_score), 1.0)
    
    # ---------------------------------------------------------------
    # Step 6: Build human-readable reasoning
    # ---------------------------------------------------------------
    pattern_summary = ", ".join(
        f"{s['pattern']} ({s['confidence']:.0%} conf, {s['signal']})"
        for s in individual_signals
    )
    
    reasoning = (
        f"Pattern Analysis Results:\n"
        f"Patterns detected: {pattern_summary}\n"
        f"Weighted score: {avg_score:+.3f} "
        f"(BUY threshold: >{BUY_THRESHOLD:+.1f}, "
        f"SELL threshold: <{SELL_THRESHOLD:+.1f})\n"
        f"Signal: {final_signal} with {signal_confidence:.0%} confidence.\n"
    )
    
    # Add pattern-specific insights
    for sig in individual_signals:
        reasoning += f"\n• {sig['pattern']}: {sig['description']}"
    
    logger.info(
        f"[SIGNAL] {final_signal} (score={avg_score:+.3f}, "
        f"confidence={signal_confidence:.0%})"
    )
    
    return TradingSignal(
        signal=final_signal,
        confidence=round(signal_confidence, 4),
        score=round(avg_score, 4),
        patterns_detected=[p.name for p in valid_patterns],
        reasoning=reasoning,
        individual_signals=individual_signals,
    )
