from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from langchain_core.messages import HumanMessage, AIMessage
from backend.agents.stock_agent import graph, saver
from backend.db.db import get_db, release_db, init_db
from fastapi.middleware.cors import CORSMiddleware
import uuid
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

import json

def filter_messages(messages):
    """
    Filters out internal tool calls and observations, leaving only 
    genuine User and Assistant messages.
    """
    filtered = []
    for msg in messages:
        content = msg.content.strip() if hasattr(msg, 'content') else ""
        
        is_tool_call = False
        try:
            if content.startswith('{') and content.endswith('}'):
                parsed = json.loads(content)
                if parsed.get("action") == "tool":
                    is_tool_call = True
        except:
            pass

        is_internal_human = isinstance(msg, HumanMessage) and (
            content.startswith("Observation from") or 
            content.startswith("SYSTEM NOTICE") or 
            content.startswith("SYSTEM ERROR")
        )

        if not is_tool_call and not is_internal_human:
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

@app.post("/analyze")
def analyze_stock(req: StockRequest):
    thread_id = req.thread_id or str(uuid.uuid4())
    print(f"\n[BACKEND] Received query: {req.query}")
    print(f"[BACKEND] Thread ID: {thread_id}")
    
    # Update or create thread metadata
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT title FROM threads WHERE id = %s", (thread_id,))
            row = cur.fetchone()
            if not row:
                # First message, use it as title
                title = req.query[:50] + ("..." if len(req.query) > 50 else "")
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

    config = {"configurable": {"thread_id": thread_id}}
    
    try:
        result = graph.invoke({
            "messages": [HumanMessage(content=req.query)],
            "loop_count": 0
        }, config=config)

        # Use our filtering logic to find the actual response
        filtered = filter_messages(result["messages"])
        # The last filtered message should be the AI's final answer
        final_response = "I've analyzed the data, but I'm having trouble providing a final answer. Please try a different query."
        
        # Look for the last assistant message in the filtered list
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
