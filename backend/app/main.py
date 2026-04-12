from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from agents.stock_agent import graph, saver, StockAnalysisResponse
from db.db import get_db, release_db, init_db
from ingestion.tool import fetch_stock_dashboard_data
from trading.broker import get_account_info, get_positions, get_recent_orders
from pattern_detection.pattern_detector import analyze_chart
from trading.signal_engine import generate_signal
from fastapi.middleware.cors import CORSMiddleware
import uuid
import json
from langgraph.checkpoint.postgres import PostgresSaver

app = FastAPI()

@app.on_event("startup")
def startup_event():
    import psycopg
    import os

    init_db()

    conn_info = os.getenv("DATABASE_URL") + "?sslmode=require"
    try:
        with psycopg.connect(conn_info, autocommit=True) as conn:

            setup_saver = PostgresSaver(conn)
            setup_saver.setup()
            print("[DB] PostgresSaver tables ensured (autocommit).")
    except Exception as e:
        print(f"[DB] Warning: PostgresSaver setup failed: {e}")
        try:
            saver.setup()
            print("[DB] PostgresSaver tables ensured (fallback).")
        except Exception as e2:
            print(f"[DB] Error: Persistent storage setup totally failed: {e2}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class StockRequest(BaseModel):
    query: str
    thread_id: Optional[str] = None

@app.get("/threads")
def get_threads():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, title, updated_at FROM threads ORDER BY updated_at DESC")
            return cur.fetchall()
    finally:
        release_db(conn)


def filter_messages(messages):
    """
    Filters out internal tool calls, tool messages, and system observations,
    leaving only genuine User and Assistant messages.
    """
    filtered = []
    for msg in messages:
        content = msg.content.strip() if hasattr(msg, 'content') else ""

        # Skip ToolMessages entirely (internal)
        if isinstance(msg, ToolMessage):
            continue

        # Skip AIMessages that are pure tool calls (no text content)
        if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls and not content:
            continue

        # Skip internal system HumanMessages
        is_internal_human = isinstance(msg, HumanMessage) and (
            content.startswith("Observation from") or
            content.startswith("SYSTEM NOTICE") or
            content.startswith("SYSTEM ERROR")
        )

        if not is_internal_human:
            role = "user" if isinstance(msg, HumanMessage) else "assistant"
            filtered.append({"role": role, "content": msg.content})

    return filtered

@app.get("/threads/{thread_id}")
def get_thread_history(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    state = graph.get_state(config)
    messages = state.values.get("messages", [])
    return {"messages": filter_messages(messages)}

@app.delete("/threads/{thread_id}")
def delete_thread(thread_id: str):
    conn = get_db()
    try:
        with conn.cursor() as cur:

            cur.execute("DELETE FROM checkpoints WHERE thread_id = %s", (thread_id,))
            cur.execute("DELETE FROM checkpoint_blobs WHERE thread_id = %s", (thread_id,))
            cur.execute("DELETE FROM checkpoint_writes WHERE thread_id = %s", (thread_id,))

            cur.execute("DELETE FROM threads WHERE id = %s", (thread_id,))
            conn.commit()
            return {"status": "success"}
    except Exception as e:
        print(f"[ERROR] Failed to delete thread: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        release_db(conn)


def _upsert_thread(thread_id: str, query: str):
    """Create or update thread metadata."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT title FROM threads WHERE id = %s", (thread_id,))
            row = cur.fetchone()
            if not row:
                title = query[:50] + ("..." if len(query) > 50 else "")
                cur.execute(
                    "INSERT INTO threads (id, title, updated_at) VALUES (%s, %s, CURRENT_TIMESTAMP)",
                    (thread_id, title)
                )
            else:
                cur.execute(
                    "UPDATE threads SET updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (thread_id,)
                )
            conn.commit()
    finally:
        release_db(conn)


@app.post("/analyze")
def analyze_stock(req: StockRequest):
    """Standard (non-streaming) analysis endpoint — backward compatible."""
    thread_id = req.thread_id or str(uuid.uuid4())
    print(f"\n[BACKEND] Received query: {req.query}")
    print(f"[BACKEND] Thread ID: {thread_id}")

    _upsert_thread(thread_id, req.query)

    config = {"configurable": {"thread_id": thread_id}}

    try:
        result = graph.invoke({
            "messages": [HumanMessage(content=req.query)],
            "loop_count": 0
        }, config=config)

        # Use filtering logic to find the actual response
        filtered = filter_messages(result["messages"])
        final_response = "I've analyzed the data, but I'm having trouble providing a final answer. Please try a different query."

        # Look for the last assistant message
        for msg in reversed(filtered):
            if msg["role"] == "assistant":
                final_response = msg["content"]
                break

        return {
            "response": final_response,
            "thread_id": thread_id
        }
    except Exception as e:
        print(f"[ERROR] Backend processing failed: {e}")
        return {
            "response": f"I'm sorry, an error occurred: {str(e)}",
            "thread_id": thread_id
        }



@app.post("/agent/stock")
def get_dashboard_data(req: Dict[str, str]):
    symbol = req.get("symbol")
    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol is required")

    try:
        from ingestion.tool import fetch_stock_dashboard_data
        return fetch_stock_dashboard_data(symbol)
    except Exception as e:
        print(f"[ERROR] Dashboard fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# NEW: TRADING & PATTERN DETECTION API ENDPOINTS
# =============================================================================
# These endpoints provide direct REST access to the pattern detection engine
# and Alpaca broker. They bypass the LLM agent loop for faster responses
# and are used by the frontend TradingPanel component.
# =============================================================================

@app.get("/trading/account")
def get_trading_account():
    """
    GET /trading/account
    
    Returns the Alpaca trading account information:
    cash, buying power, equity, portfolio value, etc.
    
    Used by the frontend TradingPanel to display account overview.
    """
    try:
        return get_account_info()
    except Exception as e:
        print(f"[ERROR] Trading account fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/trading/positions")
def get_trading_positions():
    """
    GET /trading/positions
    
    Returns all open positions from the Alpaca broker:
    symbol, qty, market value, P&L, etc.
    
    Used by the frontend TradingPanel to display the portfolio table.
    """
    try:
        return get_positions()
    except Exception as e:
        print(f"[ERROR] Positions fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/trading/scan/{symbol}")
def scan_chart_patterns(symbol: str):
    """
    POST /trading/scan/{symbol}
    
    Runs the full pattern detection + signal generation pipeline:
    1. Fetches OHLCV data for the symbol
    2. Generates a candlestick chart image
    3. Runs YOLOv8 pattern detection
    4. Generates BUY/SELL/HOLD signal
    
    This is the main endpoint for the pattern scanner in the TradingPanel.
    It bypasses the LLM agent for speed (~5-10 seconds total).
    
    Args:
        symbol: Stock ticker (path parameter, e.g., /trading/scan/AAPL)
    
    Returns:
        Dictionary with patterns, signal, confidence, and reasoning.
    """
    try:

        # Step 1: Run YOLOv8 pattern detection
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

        # Step 2: Generate trading signal from detected patterns
        signal = generate_signal(analysis.patterns)

        return {
            "symbol": analysis.symbol,
            "patterns": [
                {
                    "name": p.name,
                    "confidence": round(p.confidence * 100, 1),
                }
                for p in analysis.patterns
            ],
            "signal": signal.signal,
            "signal_confidence": round(signal.confidence * 100, 1),
            "score": signal.score,
            "reasoning": signal.reasoning,
            "individual_signals": signal.individual_signals,
            "timestamp": analysis.analysis_timestamp,
        }
    except Exception as e:
        print(f"[ERROR] Pattern scan failed for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/trading/orders")
def get_trading_orders():
    """
    GET /trading/orders
    
    Returns the 10 most recent orders from Alpaca:
    order ID, symbol, qty, side, status, timestamps, etc.
    
    Used by the frontend TradingPanel to display order history.
    """
    try:
        return get_recent_orders(limit=10)
    except Exception as e:
        print(f"[ERROR] Orders fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
