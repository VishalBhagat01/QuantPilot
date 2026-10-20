"""Centralized, deterministic safety checks for user, tool, and model content."""

import re
import json
import time
from threading import Lock
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

MAX_QUERY_LENGTH = 4000
MAX_RESPONSE_LENGTH = 25000
MAX_TOOL_CALLS = 12
MAX_SYMBOL_LENGTH = 10
PENDING_TRADE_TTL_SECONDS = 300

_SYMBOL_PATTERN = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")
_CONTROL_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SECRET_PATTERNS = (
    re.compile(r"(?i)\b(?:api[_ -]?key|access[_ -]?token|secret[_ -]?key)\s*[:=]\s*\S+"),
    re.compile(r"\beyJ[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\b"),
)
_PROMPT_INJECTION_PATTERNS = (
    re.compile(r"(?i)\bignore\s+(?:all\s+)?(?:previous|prior|system)\s+instructions\b"),
    re.compile(r"(?i)\b(?:reveal|show|print|输出)\b.{0,40}\b(?:system prompt|developer message|api key|secret|token)\b"),
    re.compile(r"(?i)\b(?:bypass|disable|override)\b.{0,30}\b(?:auth|guardrail|risk|limit|policy)\b"),
)
_UNSAFE_FINANCIAL_CLAIMS = (
    (re.compile(r"(?i)\bguaranteed?\s+(?:profit|return|gains?)\b"), "potential returns are not guaranteed"),
    (re.compile(r"(?i)\brisk[- ]?free\b"), "lower-risk, but not risk-free"),
    (re.compile(r"(?i)\bwill\s+definitely\s+(?:rise|go up|fall|drop)\b"), "may rise or fall"),
)
_INTERNAL_CONTENT_PATTERN = re.compile(
    r"(?i)(?:ERROR executing|traceback \(most recent call last\))"
)
_TRADE_CONFIRMATION_PATTERN = re.compile(
    r"(?i)\b(?:confirm|execute|submit|send)\b.{0,30}\b(?:order|trade|position)\b"
)
_DASHBOARD_PATTERN = re.compile(r"(?im)^\s*DASHBOARD:([A-Z][A-Z0-9.\-]{0,9})\s*$")
_DOMAIN_TERMS = re.compile(
    r"(?i)\b(?:stock|stocks|share|shares|equity|equities|"
    r"market|markets|finance|financial|invest|investment|investing|portfolio|"
    r"trading|trade|trader|ticker|etf|fund|mutual fund|dividend|earnings?|"
    r"revenue|valuation|fundamentals?|quote|price|chart|technical analysis|"
    r"indicator|rsi|macd|moving average|candlestick|beta|sharpe|"
    r"broker|brokerage|position|order|buy|sell|short|stop[- ]loss|"
    r"company|sector|index|indices|nasdaq|nyse|s&p|dow jones|news|"
    r"crypto(?:currency)?|bitcoin|ethereum|gold|silver|commodity|"
    r"forex|p/e|pe ratio|eps|roi|return|cagr|risk|allocation|"
    r"diversif(?:y|ication)|market cap|cash flow|balance sheet|"
    r"financial model|paper trading|account|balance|cash|buying power|"
    r"holding|holdings)\b"
)
_FINANCIAL_MATH_TERMS = re.compile(
    r"(?i)\b(?:calculate|compute|formula|percentage|percent|compound interest|"
    r"position size|risk/reward|standard deviation|correlation|projection|"
    r"profit|loss|gain|yield|growth rate)\b"
)


class DomainDecision(str, Enum):
    """Classification result for the supported assistant domain."""

    IN_SCOPE = "in_scope"
    OUT_OF_SCOPE = "out_of_scope"
    AMBIGUOUS = "ambiguous"


DOMAIN_REJECTION_MESSAGE = (
    "I can help with stock markets, financial analysis, portfolios, and supported "
    "trading features. Please ask a question related to those topics."
)

_pending_trades: dict[tuple[str, str], tuple[dict[str, Any], float]] = {}
_pending_trades_lock = Lock()

class GuardrailViolation(ValueError):
    """Raised when a request or tool call violates a safety policy."""


@dataclass(frozen=True)
class InputCheck:
    query: str
    is_prompt_injection: bool


@dataclass(frozen=True)
class DomainCheck:
    decision: DomainDecision

    @property
    def allowed(self) -> bool:
        return self.decision is DomainDecision.IN_SCOPE


def classify_query_domain(query: str) -> DomainCheck:
    """Classify a normalized query without invoking an LLM or application tools."""
    if not isinstance(query, str) or not query.strip():
        return DomainCheck(DomainDecision.AMBIGUOUS)

    normalized = " ".join(query.split())
    has_domain_term = bool(_DOMAIN_TERMS.search(normalized))
    has_financial_math = bool(_FINANCIAL_MATH_TERMS.search(normalized)) and has_domain_term
    if has_domain_term or has_financial_math:
        return DomainCheck(DomainDecision.IN_SCOPE)

    return DomainCheck(DomainDecision.AMBIGUOUS)


def validate_query(query: str) -> InputCheck:
    """Normalize and validate an analysis query before it reaches the agent."""
    if not isinstance(query, str):
        raise GuardrailViolation("Query must be text.")

    normalized = " ".join(query.split())
    if not normalized:
        raise GuardrailViolation("Query cannot be empty.")
    if len(normalized) > MAX_QUERY_LENGTH:
        raise GuardrailViolation(
            f"Query exceeds the {MAX_QUERY_LENGTH}-character limit."
        )
    if _CONTROL_PATTERN.search(normalized):
        raise GuardrailViolation("Query contains unsupported control characters.")

    return InputCheck(
        query=normalized,
        is_prompt_injection=any(pattern.search(normalized) for pattern in _PROMPT_INJECTION_PATTERNS),
    )


def validate_symbol(symbol: Any) -> str:
    """Return a normalized ticker or raise for an invalid ticker value."""
    if not isinstance(symbol, str):
        raise GuardrailViolation("Symbol must be text.")
    normalized = symbol.strip().upper()
    if not _SYMBOL_PATTERN.fullmatch(normalized):
        raise GuardrailViolation("Invalid ticker symbol.")
    return normalized


def validate_tool_call(
    tool_name: str,
    tool_args: Mapping[str, Any],
    *,
    user_id: str | None,
    tool_call_count: int,
    trade_confirmed: bool = False,
    thread_id: str | None = None,
) -> dict[str, Any]:
    """Validate an agent tool call and return normalized arguments."""
    if tool_call_count >= MAX_TOOL_CALLS:
        raise GuardrailViolation("This request exceeded the tool-call safety limit.")

    if not isinstance(tool_args, Mapping):
        raise GuardrailViolation("Tool arguments must be an object.")

    symbol_tools = {
        "get_stock_price", "get_stock_news", "get_old_news", "get_stock_price2",
        "get_stock_news2", "company_inside_news", "company_overview",
        "annual_income_statement", "earning_estimate", "future_expected_earning",
        "get_stock_intraday_chart", "predict_stock_signal",
    }
    if tool_name in symbol_tools:
        args = dict(tool_args)
        args["symbol"] = validate_symbol(args.get("symbol"))
        return args

    if tool_name in {"get_broker_account", "get_broker_positions"} and not user_id:
        raise GuardrailViolation("Authenticated broker context is required.")

    allowed_tools = {
        "get_stock_price", "get_stock_news", "get_old_news", "search_tool",
        "get_stock_price2", "get_stock_news2", "company_inside_news", "top_gainers",
        "company_overview", "annual_income_statement", "earning_estimate",
        "future_expected_earning", "get_gold_price", "get_silver_price",
        "get_stock_intraday_chart", "predict_stock_signal", "get_broker_account",
        "get_broker_positions", "place_trade", "close_trade",
    }
    if tool_name not in allowed_tools:
        raise GuardrailViolation("This tool is not allowed.")

    if tool_name == "search_tool":
        query = tool_args.get("query")
        if not isinstance(query, str) or not query.strip() or len(query.strip()) > 500:
            raise GuardrailViolation("Search query must contain 1 to 500 characters.")
        return {"query": " ".join(query.split())}

    if tool_name in {"get_gold_price", "get_silver_price", "top_gainers"}:
        if tool_args:
            raise GuardrailViolation("This tool does not accept arguments.")
        return {}

    if tool_name == "place_trade":
        if not user_id:
            raise GuardrailViolation("Authenticated broker context is required.")
        args = dict(tool_args)
        args["symbol"] = validate_symbol(args.get("symbol"))
        if tool_name == "place_trade":
            side = str(args.get("side", "")).strip().lower()
            if side not in {"buy", "sell"}:
                raise GuardrailViolation("Side must be 'buy' or 'sell'.")
            args["side"] = side
            if not isinstance(args.get("qty"), int) or args["qty"] <= 0:
                raise GuardrailViolation("Quantity must be a positive whole number.")
            args["order_type"] = str(args.get("order_type", "market")).strip().lower()
            args["time_in_force"] = str(args.get("time_in_force", "day")).strip().lower()
            args["limit_price"] = args.get("limit_price")
            if not trade_confirmed:
                create_pending_trade(user_id, thread_id, args)
                raise GuardrailViolation(
                    "Trade proposal created. Ask the user to explicitly confirm this exact order."
                )
            if not consume_pending_trade(user_id, thread_id, args):
                raise GuardrailViolation(
                    "No matching unexpired trade proposal was found. Create a new proposal first."
                )
        return args

    if tool_name == "close_trade":
        if not user_id:
            raise GuardrailViolation("Authenticated broker context is required.")
        args = dict(tool_args)
        args["symbol"] = validate_symbol(args.get("symbol"))
        proposal = {
            "symbol": args["symbol"],
            "qty": 0,
            "side": "close",
            "order_type": "market",
            "limit_price": None,
            "time_in_force": "day",
        }
        if not trade_confirmed:
            create_pending_trade(user_id, thread_id, proposal)
            raise GuardrailViolation(
                "Close proposal created. Ask the user to explicitly confirm this exact position close."
            )
        if not consume_pending_trade(user_id, thread_id, proposal):
            raise GuardrailViolation(
                "No matching unexpired close proposal was found. Create a new proposal first."
            )
        return args

    return dict(tool_args)


def is_trade_confirmation(content: Any) -> bool:
    """Identify explicit order confirmation language in the user's latest message."""
    return isinstance(content, str) and bool(_TRADE_CONFIRMATION_PATTERN.search(content))


def _trade_key(user_id: str | None, thread_id: str | None) -> tuple[str, str]:
    if not user_id or not thread_id:
        raise GuardrailViolation("A user and thread are required for trade confirmation.")
    return user_id, thread_id


def _purge_pending_trades(now: float) -> None:
    expired = [key for key, (_, expires_at) in _pending_trades.items() if expires_at <= now]
    for key in expired:
        _pending_trades.pop(key, None)


def _canonical_trade(args: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "symbol": validate_symbol(args.get("symbol")),
        "qty": int(args["qty"]),
        "side": str(args["side"]).strip().lower(),
        "order_type": str(args.get("order_type", "market")).strip().lower(),
        "limit_price": args.get("limit_price"),
        "time_in_force": str(args.get("time_in_force", "day")).strip().lower(),
    }


def create_pending_trade(user_id: str | None, thread_id: str | None, args: Mapping[str, Any]) -> dict[str, Any]:
    """Store one short-lived proposal per user/thread without exposing secrets."""
    key = _trade_key(user_id, thread_id)
    canonical = _canonical_trade(args)
    with _pending_trades_lock:
        _purge_pending_trades(time.time())
        _pending_trades[key] = (canonical, time.time() + PENDING_TRADE_TTL_SECONDS)
    try:
        from backend.db.db import db_session

        with db_session() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO pending_trades (user_id, thread_id, payload, expires_at)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP + INTERVAL '5 minutes')
                    ON CONFLICT (user_id, thread_id) DO UPDATE SET
                        payload = EXCLUDED.payload,
                        expires_at = EXCLUDED.expires_at
                    """,
                    (user_id, thread_id, json.dumps(canonical, sort_keys=True)),
                )
            conn.commit()
    except Exception:
        pass
    return canonical


def consume_pending_trade(
    user_id: str | None,
    thread_id: str | None,
    args: Mapping[str, Any],
) -> bool:
    """Atomically consume an exact proposal so duplicate confirmations cannot execute twice."""
    key = _trade_key(user_id, thread_id)
    canonical = _canonical_trade(args)
    try:
        from backend.db.db import db_session

        with db_session() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT payload FROM pending_trades
                    WHERE user_id = %s AND thread_id = %s
                      AND expires_at > CURRENT_TIMESTAMP
                    FOR UPDATE
                    """,
                    (user_id, thread_id),
                )
                row = cursor.fetchone()
                if row and json.loads(row["payload"]) == canonical:
                    cursor.execute(
                        "DELETE FROM pending_trades WHERE user_id = %s AND thread_id = %s",
                        (user_id, thread_id),
                    )
                    conn.commit()
                    with _pending_trades_lock:
                        _pending_trades.pop(key, None)
                    return True
                conn.rollback()
                return False
    except Exception:
        pass

    with _pending_trades_lock:
        _purge_pending_trades(time.time())
        pending = _pending_trades.get(key)
        if pending is None or pending[0] != canonical:
            return False
        _pending_trades.pop(key, None)
        return True


def clear_pending_trade(user_id: str | None, thread_id: str | None) -> None:
    """Remove a proposal after execution or cancellation."""
    if not user_id or not thread_id:
        return
    with _pending_trades_lock:
        _pending_trades.pop((user_id, thread_id), None)
    try:
        from backend.db.db import db_session

        with db_session() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM pending_trades WHERE user_id = %s AND thread_id = %s",
                    (user_id, thread_id),
                )
            conn.commit()
    except Exception:
        pass


def sanitize_output(content: Any, *, add_disclaimer: bool = True) -> str:
    """Bound and sanitize model output before it is returned to a client."""
    text = str(content or "").strip()
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    text = _INTERNAL_CONTENT_PATTERN.sub("The requested operation was blocked.", text)
    for pattern, replacement in _UNSAFE_FINANCIAL_CLAIMS:
        text = pattern.sub(replacement, text)
    if not text:
        text = "I could not produce a reliable answer. Please rephrase your request."
    if add_disclaimer and not text.lower().startswith("hello") and "not financial advice" not in text.lower():
        text += (
            "\n\nThis information is for research and educational purposes only and "
            "is not financial advice. Market data may be delayed or incomplete."
        )
    if len(text) > MAX_RESPONSE_LENGTH:
        text = text[:MAX_RESPONSE_LENGTH].rstrip() + "\n\n[Response truncated.]"
    return text


def validate_final_response(content: Any, *, add_disclaimer: bool = True) -> str:
    """Validate final model text while preserving the existing dashboard marker."""
    text = sanitize_output(content, add_disclaimer=add_disclaimer)
    markers = _DASHBOARD_PATTERN.findall(text)
    if markers:
        ticker = validate_symbol(markers[-1])
        text = _DASHBOARD_PATTERN.sub(f"DASHBOARD:{ticker}", text)
    return text


def safe_error_message(error: Exception) -> str:
    """Return a user-safe error without provider details or stack traces."""
    message = str(error).strip()
    for pattern in _SECRET_PATTERNS:
        message = pattern.sub("[REDACTED]", message)
    if len(message) > 300:
        message = message[:300].rstrip() + "..."
    return message or "The request could not be completed."
