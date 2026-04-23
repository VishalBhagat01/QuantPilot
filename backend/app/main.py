from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from backend.agents.stock_agent import graph, saver
from backend.db.db import get_db, release_db, init_db
from backend.ingestion.tool import fetch_stock_dashboard_data, predict_stock_signal
from backend.trading.broker import get_account_info, get_positions, get_recent_orders
from fastapi.middleware.cors import CORSMiddleware
import uuid
from langgraph.checkpoint.postgres import PostgresSaver

app = FastAPI()

@app.on_event("startup")
def startup_event():
    import psycopg
    import os

    # All DB setup is best-effort — app must start even if DB is temporarily unreachable
    try:
        init_db()
    except Exception as e:
        print(f"[DB] Warning: init_db failed ({e}), will retry on first request.")

    db_url = os.getenv("DATABASE_URL", "").strip()
    if not db_url:
        print("[DB] Warning: DATABASE_URL not set, skipping PostgresSaver setup.")
        return

    conninfo = db_url if "sslmode" in db_url else db_url + "?sslmode=require"
    try:
        with psycopg.connect(conninfo, autocommit=True, connect_timeout=10) as conn:
            setup_saver = PostgresSaver(conn)
            setup_saver.setup()
            print("[DB] PostgresSaver tables ensured (autocommit).")
    except Exception as e:
        print(f"[DB] Warning: PostgresSaver setup failed: {e}")
        try:
            if saver:
                saver.setup()
                print("[DB] PostgresSaver tables ensured (fallback).")
        except Exception as e2:
            print(f"[DB] Warning: Persistent storage setup failed: {e2}")

    print("[STARTUP] App ready.")

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
    """Return only user/assistant chat messages for frontend display."""
    filtered = []
    for msg in messages:
        raw_content = getattr(msg, "content", "")
        if isinstance(raw_content, list):
            text_parts = []
            for part in raw_content:
                if isinstance(part, dict):
                    text_parts.append(part.get("text", ""))
                else:
                    text_parts.append(str(part))
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
    """Non-streaming stock analysis endpoint."""
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

        filtered = filter_messages(result["messages"])
        final_response = "I've analyzed the data, but I'm having trouble providing a final answer. Please try a different query."

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
        return fetch_stock_dashboard_data(symbol)
    except Exception as e:
        print(f"[ERROR] Dashboard fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/trading/account")
def get_trading_account():
    """Return Alpaca trading account details."""
    try:
        return get_account_info()
    except Exception as e:
        print(f"[ERROR] Trading account fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/trading/positions")
def get_trading_positions():
    """Return all open Alpaca positions."""
    try:
        return get_positions()
    except Exception as e:
        print(f"[ERROR] Positions fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/trading/scan/{symbol}")
def scan_chart_patterns(symbol: str):
    """Run technical-analysis scan and return BUY/SELL/HOLD signal."""
    try:
        result = predict_stock_signal.invoke({"symbol": symbol})

        if result.get("error"):
            return {
                "symbol": symbol,
                "error": result["error"],
                "signal": "HOLD",
                "confidence": "0%",
                "reasoning": f"Analysis failed: {result['error']}",
            }

        return {
            "symbol": result.get("symbol"),
            "signal": result.get("signal"),
            "confidence": result.get("confidence"),
            "reasoning": result.get("reasoning"),
            "indicators": result.get("indicators", {}),
            "timestamp": "generated_now"
        }
    except Exception as e:
        print(f"[ERROR] Trading scan failed for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/trading/orders")
def get_trading_orders():
    """Return recent Alpaca orders."""
    try:
        return get_recent_orders(limit=10)
    except Exception as e:
        print(f"[ERROR] Orders fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
