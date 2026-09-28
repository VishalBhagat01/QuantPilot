"""FastAPI backend application for QuantPilot."""

import sys
import uuid
import datetime
import logging
from contextlib import asynccontextmanager
from typing import Optional, Dict

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from backend.core.config import settings
from backend.agents.stock_agent import graph
from backend.db.db import get_db, release_db, init_db, check_db_availability
from backend.ingestion.tool import fetch_stock_dashboard_data, predict_stock_signal
from backend.trading.broker import get_account_info, get_positions, get_recent_orders

logger = logging.getLogger(__name__)

# Fallback in-memory thread storage if PostgreSQL is unreachable
_memory_threads: Dict[str, Dict] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI modern lifespan context manager for startup and shutdown hooks."""
    logger.info("[STARTUP] Initializing QuantPilot backend...")

    # Best-effort DB initialization
    try:
        if check_db_availability():
            init_db()
            db_url = settings.database_url
            conninfo = db_url if "sslmode" in db_url else f"{db_url}?sslmode=require"
            with psycopg.connect(conninfo, autocommit=True, connect_timeout=3) as conn:
                setup_saver = PostgresSaver(conn)
                setup_saver.setup()
                logger.info("[DB] PostgresSaver tables verified.")
    except Exception as e:
        logger.warning(f"[DB] Notice: DB setup skipped ({e}). In-memory fallback active.")

    logger.info("[STARTUP] Application ready.")
    yield
    logger.info("[SHUTDOWN] QuantPilot backend shutting down.")


app = FastAPI(title="QuantPilot API", lifespan=lifespan)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class StockRequest(BaseModel):
    query: str
    thread_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Thread & Session Management
# ---------------------------------------------------------------------------

def _upsert_thread(thread_id: str, query: str):
    """Create or update thread metadata (Postgres with in-memory fallback)."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    title = query[:50] + ("..." if len(query) > 50 else "")

    if thread_id not in _memory_threads:
        _memory_threads[thread_id] = {"title": title, "updated_at": now}
    else:
        _memory_threads[thread_id]["updated_at"] = now

    try:
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO threads (id, title, updated_at)
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (id) DO UPDATE SET updated_at = CURRENT_TIMESTAMP;
                """, (thread_id, title))
                conn.commit()
        finally:
            release_db(conn)
    except Exception:
        pass


def filter_messages(messages):
    """Format and filter LangGraph messages for frontend display."""
    filtered = []
    for msg in messages:
        raw_content = getattr(msg, "content", "")
        if isinstance(raw_content, list):
            text_parts = [p.get("text", "") if isinstance(p, dict) else str(p) for p in raw_content]
            text_content = "".join(text_parts)
        else:
            text_content = str(raw_content) if raw_content else ""

        clean_content = text_content.strip()

        if isinstance(msg, ToolMessage):
            continue

        if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls and not clean_content:
            continue

        is_internal_human = isinstance(msg, HumanMessage) and (
            clean_content.startswith("Observation from") or
            clean_content.startswith("SYSTEM NOTICE") or
            clean_content.startswith("SYSTEM ERROR")
        )

        if not is_internal_human:
            role = "user" if isinstance(msg, HumanMessage) else "assistant"
            filtered.append({"role": role, "content": clean_content})

    return filtered


@app.get("/threads")
def get_threads():
    """Retrieve all conversations, ordered by latest activity."""
    try:
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id, title, updated_at FROM threads ORDER BY updated_at DESC")
                return cur.fetchall()
        finally:
            release_db(conn)
    except Exception:
        return sorted(
            [{"id": k, "title": v["title"], "updated_at": v["updated_at"]} for k, v in _memory_threads.items()],
            key=lambda x: str(x["updated_at"]),
            reverse=True
        )


@app.get("/threads/{thread_id}")
def get_thread_history(thread_id: str):
    """Retrieve message history for a specific thread."""
    try:
        config = {"configurable": {"thread_id": thread_id}}
        state = graph.get_state(config)
        messages = state.values.get("messages", [])
        return {"messages": filter_messages(messages)}
    except Exception as e:
        logger.warning(f"[THREADS] Could not retrieve history for {thread_id}: {e}")
        return {"messages": []}


@app.delete("/threads/{thread_id}")
def delete_thread(thread_id: str):
    """Delete a thread and associated checkpoints."""
    _memory_threads.pop(thread_id, None)
    try:
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM checkpoints WHERE thread_id = %s", (thread_id,))
                cur.execute("DELETE FROM checkpoint_blobs WHERE thread_id = %s", (thread_id,))
                cur.execute("DELETE FROM checkpoint_writes WHERE thread_id = %s", (thread_id,))
                cur.execute("DELETE FROM threads WHERE id = %s", (thread_id,))
                conn.commit()
        finally:
            release_db(conn)
    except Exception as e:
        logger.warning(f"[THREADS] DB delete skipped: {e}")
    return {"status": "success"}


# ---------------------------------------------------------------------------
# Core Analysis Endpoint
# ---------------------------------------------------------------------------

@app.post("/analyze")
def analyze_stock(req: StockRequest):
    """Analyze query via LangGraph multi-agent orchestration."""
    thread_id = req.thread_id or str(uuid.uuid4())
    logger.info(f"[BACKEND] Query: {req.query} (thread: {thread_id})")

    _upsert_thread(thread_id, req.query)

    # Fast-path for greetings to provide instantaneous response
    clean_q = req.query.strip().lower().rstrip("!?.")
    greetings = {
        "hi", "hello", "hey", "hola", "yo", "sup", "good morning", "good evening",
        "good afternoon", "hi there", "hello there", "who are you", "what can you do", "help"
    }
    if clean_q in greetings:
        welcome_text = (
            "Hello! I am **QuantPilot**, your AI financial research and trading assistant.\n\n"
            "Here is how I can assist you:\n"
            "- **Live Quotes & Pricing**: *\"What is the price of AAPL?\"*\n"
            "- **Technical Analysis & Trading Signals**: *\"Should I buy TSLA?\"*\n"
            "- **Fundamentals & Financials**: *\"Show me NVDA valuation and P/E ratio\"*\n"
            "- **Market News**: *\"Latest news on Microsoft\"*\n"
            "- **Broker & Positions**: *\"Check my account balance and open positions\"*\n\n"
            "What stock or market query would you like to explore today?"
        )
        return {
            "response": welcome_text,
            "thread_id": thread_id
        }

    config = {"configurable": {"thread_id": thread_id}}

    try:
        result = graph.invoke({
            "messages": [HumanMessage(content=req.query)],
            "loop_count": 0
        }, config=config)

        filtered = filter_messages(result["messages"])
        final_response = "I have analyzed the data, but I am unable to format a final answer. Please rephrase your query."

        for msg in reversed(filtered):
            if msg["role"] == "assistant":
                final_response = msg["content"]
                break

        return {
            "response": final_response,
            "thread_id": thread_id
        }
    except Exception as e:
        logger.error(f"[ERROR] Agent execution failed: {e}")
        return {
            "response": f"I'm sorry, an error occurred during analysis: {str(e)}",
            "thread_id": thread_id
        }


@app.post("/agent/stock")
def get_dashboard_data(req: Dict[str, str]):
    """Directly fetch consolidated data for the StockCard UI widget."""
    symbol = req.get("symbol", "").strip().upper()
    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol is required")

    try:
        return fetch_stock_dashboard_data(symbol)
    except Exception as e:
        logger.error(f"[ERROR] Dashboard fetch failed for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Trading Terminal Endpoints
# ---------------------------------------------------------------------------

@app.get("/trading/account")
def get_trading_account():
    """Return Alpaca trading account details."""
    try:
        return get_account_info()
    except Exception as e:
        logger.error(f"[ERROR] Trading account fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/trading/positions")
def get_trading_positions():
    """Return all open Alpaca positions."""
    try:
        return get_positions()
    except Exception as e:
        logger.error(f"[ERROR] Positions fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/trading/scan/{symbol}")
def scan_chart_patterns(symbol: str):
    """
    Run technical analysis and chart pattern scan for a stock.
    Returns signal, confidence, indicators, and detected patterns.
    """
    clean_sym = symbol.strip().upper()
    if not clean_sym:
        raise HTTPException(status_code=400, detail="Invalid ticker symbol")

    try:
        tech_result = predict_stock_signal.invoke({"symbol": clean_sym})

        patterns_list = []
        try:
            from backend.pattern_detection.pattern_detector import analyze_chart
            chart_res = analyze_chart(clean_sym, period="3mo", cleanup_image=True)
            if chart_res and chart_res.patterns:
                patterns_list = [
                    {"name": p.name, "confidence": round(p.confidence * 100, 1)}
                    for p in chart_res.patterns
                ]
        except Exception as e:
            logger.info(f"[SCAN] Pattern detection skipped: {e}")

        raw_conf = tech_result.get("confidence_raw", 50)
        signal = tech_result.get("signal", "HOLD")

        return {
            "symbol": clean_sym,
            "signal": signal,
            "confidence": f"{raw_conf}%",
            "signal_confidence": raw_conf,
            "reasoning": tech_result.get("reasoning", ""),
            "indicators": tech_result.get("indicators", {}),
            "patterns": patterns_list,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"[ERROR] Trading scan failed for {clean_sym}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/trading/orders")
def get_trading_orders():
    """Return recent Alpaca orders."""
    try:
        return get_recent_orders(limit=10)
    except Exception as e:
        logger.error(f"[ERROR] Orders fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
