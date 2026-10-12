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

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import json
import asyncio
import threading
from pydantic import BaseModel
import psycopg
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from backend.core.config import settings
from backend.core.market_facts import detect_query_subject
from backend.agents.stock_agent import graph
from backend.db.db import get_db, release_db, init_db, check_db_availability
from backend.ingestion.tool import fetch_stock_dashboard_data, predict_stock_signal
from backend.trading.broker import get_account_info, get_positions, get_recent_orders
from backend.app.auth import verify_user
from backend.app.auth_router import router as auth_router

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

# Register distributed routers
app.include_router(auth_router)


class StockRequest(BaseModel):
    query: str
    thread_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Thread & Session Management
# ---------------------------------------------------------------------------

def _upsert_thread(thread_id: str, query: str, user_id: str):
    """Create or update thread metadata (Postgres with in-memory fallback)."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    title = query[:50] + ("..." if len(query) > 50 else "")

    if thread_id not in _memory_threads:
        _memory_threads[thread_id] = {"title": title, "updated_at": now, "user_id": user_id}
    else:
        _memory_threads[thread_id]["updated_at"] = now
        _memory_threads[thread_id]["user_id"] = user_id

    try:
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO threads (id, title, user_id, updated_at)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (id) DO UPDATE SET updated_at = CURRENT_TIMESTAMP, user_id = EXCLUDED.user_id;
                """, (thread_id, title, user_id))
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
def get_threads(user=Depends(verify_user)):
    """Retrieve all conversations for the user, ordered by latest activity."""
    user_id = user.id if hasattr(user, "id") else user.get("id")
    try:
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id, title, updated_at FROM threads WHERE user_id = %s ORDER BY updated_at DESC", (user_id,))
                return cur.fetchall()
        finally:
            release_db(conn)
    except Exception:
        return sorted(
            [{"id": k, "title": v["title"], "updated_at": v["updated_at"]} for k, v in _memory_threads.items() if v.get("user_id") == user_id],
            key=lambda x: str(x["updated_at"]),
            reverse=True
        )


@app.get("/threads/{thread_id}")
def get_thread_history(thread_id: str, user=Depends(verify_user)):
    """Retrieve message history for a specific thread, ensuring ownership."""
    user_id = user.id if hasattr(user, "id") else user.get("id")
    try:
        if check_db_availability():
            conn = get_db()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT id FROM threads WHERE id = %s AND user_id = %s", (thread_id, user_id))
                    if not cur.fetchone():
                        raise HTTPException(status_code=403, detail="Access denied")
            finally:
                release_db(conn)
        else:
            mem_thread = _memory_threads.get(thread_id)
            if mem_thread and mem_thread.get("user_id") != user_id:
                raise HTTPException(status_code=403, detail="Access denied")
    except HTTPException:
        raise
    except Exception:
        pass # Ignore DB errors during auth check
        
    try:
        config = {"configurable": {"thread_id": thread_id}}
        state = graph.get_state(config)
        messages = state.values.get("messages", [])
        return {"messages": filter_messages(messages)}
    except Exception as e:
        logger.warning(f"[THREADS] Could not retrieve history for {thread_id}: {e}")
        return {"messages": []}


@app.delete("/threads/{thread_id}")
def delete_thread(thread_id: str, user=Depends(verify_user)):
    """Delete a thread and associated checkpoints."""
    user_id = user.id if hasattr(user, "id") else user.get("id")
    
    # Check memory first
    mem_thread = _memory_threads.get(thread_id)
    if mem_thread and mem_thread.get("user_id") != user_id:
         raise HTTPException(status_code=403, detail="Access denied")
    _memory_threads.pop(thread_id, None)

    try:
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM threads WHERE id = %s AND user_id = %s", (thread_id, user_id))
                if not cur.fetchone():
                    raise HTTPException(status_code=403, detail="Access denied")
                
                cur.execute("DELETE FROM checkpoints WHERE thread_id = %s", (thread_id,))
                cur.execute("DELETE FROM checkpoint_blobs WHERE thread_id = %s", (thread_id,))
                cur.execute("DELETE FROM checkpoint_writes WHERE thread_id = %s", (thread_id,))
                cur.execute("DELETE FROM threads WHERE id = %s", (thread_id,))
                conn.commit()
        finally:
            release_db(conn)
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"[THREADS] DB delete skipped: {e}")
    return {"status": "success"}


# ---------------------------------------------------------------------------
# Core Analysis Endpoint
# ---------------------------------------------------------------------------

@app.post("/analyze")
def analyze_stock(req: StockRequest, user=Depends(verify_user)):
    """Analyze query via LangGraph multi-agent orchestration."""
    user_id = user.id if hasattr(user, "id") else user.get("id")
    
    # Verify thread ownership if thread_id is provided
    if req.thread_id:
        try:
            if check_db_availability():
                conn = get_db()
                try:
                    with conn.cursor() as cur:
                        cur.execute("SELECT user_id FROM threads WHERE id = %s", (req.thread_id,))
                        row = cur.fetchone()
                        if row and row["user_id"] != user_id:
                            raise HTTPException(status_code=403, detail="Cannot use another user's thread")
                finally:
                    release_db(conn)
            else:
                mem_thread = _memory_threads.get(req.thread_id)
                if mem_thread and mem_thread.get("user_id") != user_id:
                    raise HTTPException(status_code=403, detail="Cannot use another user's thread")
        except HTTPException:
            raise
        except Exception:
            pass # Ignore DB errors during auth check
            
    thread_id = req.thread_id or str(uuid.uuid4())
    logger.info(f"[BACKEND] Query: {req.query} (thread: {thread_id}, user: {user_id})")

    _upsert_thread(thread_id, req.query, user_id)

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


@app.post("/analyze/stream")
async def analyze_stock_stream(req: StockRequest, user=Depends(verify_user)):
    """Analyze query with progressive SSE streaming, speculative acknowledgment and market trivia."""
    user_id = user.id if hasattr(user, "id") else user.get("id")

    # Verify thread ownership if thread_id is provided
    if req.thread_id:
        try:
            if check_db_availability():
                conn = get_db()
                try:
                    with conn.cursor() as cur:
                        cur.execute("SELECT user_id FROM threads WHERE id = %s", (req.thread_id,))
                        row = cur.fetchone()
                        if row and row["user_id"] != user_id:
                            raise HTTPException(status_code=403, detail="Cannot use another user's thread")
                finally:
                    release_db(conn)
            else:
                mem_thread = _memory_threads.get(req.thread_id)
                if mem_thread and mem_thread.get("user_id") != user_id:
                    raise HTTPException(status_code=403, detail="Cannot use another user's thread")
        except HTTPException:
            raise
        except Exception:
            pass

    thread_id = req.thread_id or str(uuid.uuid4())
    logger.info(f"[BACKEND STREAM] Query: {req.query} (thread: {thread_id}, user: {user_id})")

    _upsert_thread(thread_id, req.query, user_id)

    clean_q = req.query.strip().lower().rstrip("!?.")
    greetings = {
        "hi", "hello", "hey", "hola", "yo", "sup", "good morning", "good evening",
        "good afternoon", "hi there", "hello there", "who are you", "what can you do", "help"
    }

    async def event_generator():
        # 1. Immediate speculative acknowledgment & trivia (< 50ms)
        subject_info = detect_query_subject(req.query)
        sym = subject_info.get("symbol")
        name = subject_info.get("name")
        fact = subject_info.get("fact")

        yield f"data: {json.dumps({'type': 'ack', 'thread_id': thread_id, 'symbol': sym, 'name': name, 'fact': fact})}\n\n"

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
            words = welcome_text.split(" ")
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
                await asyncio.sleep(0.015)
            yield f"data: {json.dumps({'type': 'done', 'thread_id': thread_id})}\n\n"
            return

        yield f"data: {json.dumps({'type': 'status', 'stage': 'planning', 'message': f'Formulating analysis plan for {name}...' })}\n\n"

        event_queue = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def run_graph_thread():
            try:
                config = {"configurable": {"thread_id": thread_id}}
                for chunk in graph.stream(
                    {"messages": [HumanMessage(content=req.query)], "loop_count": 0},
                    config=config,
                    stream_mode="updates"
                ):
                    loop.call_soon_threadsafe(event_queue.put_nowait, ("chunk", chunk))
                loop.call_soon_threadsafe(event_queue.put_nowait, ("done", None))
            except Exception as err:
                logger.error(f"[STREAM ERROR] Graph execution failed: {err}")
                loop.call_soon_threadsafe(event_queue.put_nowait, ("error", str(err)))

        worker_thread = threading.Thread(target=run_graph_thread, daemon=True)
        worker_thread.start()

        final_assistant_message = ""
        dashboard_ticker = sym

        while True:
            try:
                item = await asyncio.wait_for(event_queue.get(), timeout=12.0)
                event_type, payload = item

                if event_type == "chunk":
                    for node_name, node_output in payload.items():
                        if node_name == "analyst":
                            msgs = node_output.get("messages", [])
                            for m in msgs:
                                if hasattr(m, "tool_calls") and m.tool_calls:
                                    tool_names = [tc["name"] for tc in m.tool_calls]
                                    friendly_tools = []
                                    for tn in tool_names:
                                        if "price" in tn: friendly_tools.append("Real-time Quote")
                                        elif "news" in tn: friendly_tools.append("Market News")
                                        elif "signal" in tn: friendly_tools.append("Technical Indicators")
                                        elif "overview" in tn: friendly_tools.append("Company Fundamentals")
                                        elif "broker" in tn: friendly_tools.append("Broker Account")
                                        elif "trade" in tn: friendly_tools.append("Trading Engine")
                                        else: friendly_tools.append(tn)
                                    tool_desc = ", ".join(friendly_tools)
                                    yield f"data: {json.dumps({'type': 'tools_start', 'tools': tool_names, 'message': f'Executing {tool_desc}...' })}\n\n"
                                elif hasattr(m, "content") and m.content:
                                    final_assistant_message = str(m.content).strip()
                        elif node_name == "tools":
                            yield f"data: {json.dumps({'type': 'tools_done', 'message': 'Market data gathered. Synthesizing comprehensive intelligence report...' })}\n\n"
                        elif node_name == "reviewer":
                            yield f"data: {json.dumps({'type': 'status', 'stage': 'reviewing', 'message': 'Reviewing intelligence output...' })}\n\n"

                elif event_type == "done":
                    if "DASHBOARD:" in final_assistant_message:
                        try:
                            after_dash = final_assistant_message.split("DASHBOARD:")[1].strip()
                            t_cand = after_dash.split()[0].rstrip(".,;!").upper()
                            if t_cand:
                                dashboard_ticker = t_cand
                        except Exception:
                            pass

                    if not final_assistant_message:
                        final_assistant_message = "I have completed the analysis. Please check the dashboard metrics above."

                    words = final_assistant_message.split(" ")
                    for i, word in enumerate(words):
                        chunk = word + (" " if i < len(words) - 1 else "")
                        yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
                        await asyncio.sleep(0.012)

                    yield f"data: {json.dumps({'type': 'done', 'thread_id': thread_id, 'dashboard_ticker': dashboard_ticker})}\n\n"
                    break

                elif event_type == "error":
                    yield f"data: {json.dumps({'type': 'error', 'message': f'Error during analysis: {payload}'})}\n\n"
                    break

            except asyncio.TimeoutError:
                yield ": keepalive\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/agent/stock")
def get_dashboard_data(req: Dict[str, str], user=Depends(verify_user)):
    """Directly fetch consolidated data for the StockCard UI widget with dynamic timeframe."""
    symbol = req.get("symbol", "").strip().upper()
    range_param = req.get("range") or req.get("timeframe") or "1D"
    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol is required")

    try:
        return fetch_stock_dashboard_data(symbol, timeframe=range_param)
    except Exception as e:
        logger.error(f"[ERROR] Dashboard fetch failed for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Trading Terminal Endpoints
# ---------------------------------------------------------------------------

@app.get("/trading/account")
def get_trading_account(user=Depends(verify_user)):
    """Return Alpaca trading account details."""
    try:
        return get_account_info()
    except Exception as e:
        logger.error(f"[ERROR] Trading account fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/trading/positions")
def get_trading_positions(user=Depends(verify_user)):
    """Return all open Alpaca positions."""
    try:
        return get_positions()
    except Exception as e:
        logger.error(f"[ERROR] Positions fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/trading/scan/{symbol}")
def scan_chart_patterns(symbol: str, user=Depends(verify_user)):
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
def get_trading_orders(user=Depends(verify_user)):
    """Return recent Alpaca orders."""
    try:
        return get_recent_orders(limit=10)
    except Exception as e:
        logger.error(f"[ERROR] Orders fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
