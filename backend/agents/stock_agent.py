"""LangGraph multi-agent orchestration for stock analysis and algorithmic trading."""

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Annotated, List, TypedDict, Optional, Literal

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field

from backend.core.config import settings
from backend.db.db import get_pool
from backend.ingestion.tool import (
    get_stock_price,
    get_stock_news,
    get_old_news,
    search_tool,
    get_stock_price2,
    get_stock_news2,
    company_inside_news,
    top_gainers,
    company_overview,
    annual_income_statement,
    earning_estimate,
    future_expected_earning,
    get_gold_price,
    get_silver_price,
    get_stock_intraday_chart,
    predict_stock_signal,
    get_broker_account,
    get_broker_positions,
    place_trade,
    close_trade,
)

logger = logging.getLogger(__name__)

MAX_LOOPS = 3


# ---------------------------------------------------------------------------
# Structured Output Models
# ---------------------------------------------------------------------------

class ReviewerDecision(BaseModel):
    """Decision on analysis quality."""
    status: Literal["PASS", "FAIL"] = Field(description="PASS if complete, FAIL if missing info.")
    feedback: Optional[str] = Field(default=None, description="Concise feedback if FAIL.")


class DataPoint(BaseModel):
    """A single data point referenced in the analysis."""
    label: str = Field(description="Name of the metric, e.g. 'Current Price', 'P/E Ratio'")
    value: str = Field(description="The value as a string, e.g. '$150.25', '28.5'")
    source: Optional[str] = Field(default=None, description="Tool that provided this data")


class StockAnalysisResponse(BaseModel):
    """Structured final response from the stock analysis agent."""
    analysis: str = Field(description="The main analysis text in markdown format")
    data_points: List[DataPoint] = Field(default_factory=list, description="Key data points cited in analysis")
    sources: List[str] = Field(default_factory=list, description="List of tools/APIs used to gather data")
    dashboard_ticker: Optional[str] = Field(default=None, description="Stock ticker for dashboard widget, if applicable")


# ---------------------------------------------------------------------------
# LLM Initialization
# ---------------------------------------------------------------------------

google_key = settings.google_api_key
groq_key = settings.groq_api_key
llm_provider = settings.llm_provider
llm_model_name = settings.llm_model_name

primary_llm = None
backup_llm = None

# Initialize Google LLM
g_google = None
if google_key:
    try:
        model = llm_model_name if llm_provider == "google" and llm_model_name else "gemini-flash-latest"
        g_google = ChatGoogleGenerativeAI(
            model=model,
            temperature=0.1,
            google_api_key=google_key
        )
    except Exception as e:
        logger.error(f"[AGENT] Google Gemini initialization error: {e}")

# Initialize Groq LLM
g_groq = None
if groq_key:
    try:
        model = llm_model_name if llm_provider == "groq" and llm_model_name else "llama-3.3-70b-versatile"
        g_groq = ChatGroq(
            model=model,
            temperature=0,
            groq_api_key=groq_key
        )
    except Exception as e:
        logger.error(f"[AGENT] Groq initialization error: {e}")

# Assign Primary and Backup based on preferred provider
if llm_provider == "groq" and g_groq:
    primary_llm = g_groq
    backup_llm = g_google
    logger.info(f"[AGENT] Using Groq ({g_groq.model_name}) as primary LLM.")
elif g_google:
    primary_llm = g_google
    backup_llm = g_groq
    logger.info(f"[AGENT] Using Google Gemini ({g_google.model}) as primary LLM.")
elif g_groq:
    primary_llm = g_groq
    backup_llm = None
    logger.info(f"[AGENT] Using Groq ({g_groq.model_name}) as primary LLM (fallback).")

if primary_llm is None:
    raise RuntimeError("No LLM configured! Please provide a valid GOOGLE_API_KEY or GROQ_API_KEY in backend/.env")

tools_list = [
    get_stock_price,
    get_stock_news,
    get_old_news,
    search_tool,
    get_stock_price2,
    get_stock_news2,
    company_inside_news,
    top_gainers,
    company_overview,
    annual_income_statement,
    earning_estimate,
    future_expected_earning,
    get_gold_price,
    get_silver_price,
    get_stock_intraday_chart,
    predict_stock_signal,
    get_broker_account,
    get_broker_positions,
    place_trade,
    close_trade,
]

tool_map = {t.name: t for t in tools_list}
analyst_llm = primary_llm.bind_tools(tools_list)
backup_analyst_llm = backup_llm.bind_tools(tools_list) if backup_llm else None


# ---------------------------------------------------------------------------
# Agent State & Nodes
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    next_step: str
    feedback: str
    loop_count: int


def _get_text(content) -> str:
    """Normalize message content to plain string, handling multi-part list responses."""
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict):
                parts.append(part.get("text", ""))
            else:
                parts.append(str(part))
        return "".join(parts).strip()
    return str(content or "").strip()


def analyst_node(state: AgentState):
    """Analyst node: analyzes user requirements and issues tool calls or produces final analysis."""
    loop_count = state.get("loop_count", 0)
    logger.info(f"[ANALYST] Thinking (loop {loop_count})...")

    feedback = state.get("feedback", "")
    force_final = loop_count >= MAX_LOOPS - 1

    feedback_section = f"\n\nREVIEWER FEEDBACK:\n{feedback}" if feedback else ""
    force_section = (
        "\n\n MANDATORY: Maximum analysis cycles reached. Produce your final answer NOW using existing "
        "data. Do NOT make any more tool calls. End with DASHBOARD:TICKER if discussing a stock."
    ) if force_final else ""

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are the Lead Market Analyst in the QuantPilot multi-agent trading system.\n"
         "You NEVER guess market data. You ALWAYS use tools when data is needed.\n\n"
         "CORE RULES:\n"
         "1. If the user asks about ANY stock or commodity (gold, silver, etc.) → call the appropriate tool(s).\n"
         "2. You can call multiple tools simultaneously for parallel data fetching.\n"
         "3. When discussing a specific stock, end your response with: DASHBOARD:TICKER\n"
         "4. When the user asks whether to buy/sell, ALWAYS call predict_stock_signal FIRST.\n"
         "5. ALWAYS check get_broker_account to verify buying power before placing a BUY order.\n"
         "6. If the user greeting you (e.g. 'hi', 'hello', 'hey'), reply politely and briefly without calling market tools.\n"
         f"{feedback_section}"
         f"{force_section}"
        ),
        ("placeholder", "{messages}")
    ])

    chain = prompt | analyst_llm
    try:
        response = chain.invoke({"messages": state["messages"]})
        if isinstance(response, AIMessage):
            if response.content:
                response.content = _get_text(response.content)
            elif not response.tool_calls:
                return {"messages": [AIMessage(content="I encountered an issue processing your request. Please try again.")]}

        return {"messages": [response], "feedback": ""}
    except Exception as e:
        logger.error(f"[ANALYST] Primary LLM failed: {e}")
        if backup_analyst_llm:
            try:
                b_resp = (prompt | backup_analyst_llm).invoke({"messages": state["messages"]})
                return {"messages": [b_resp], "feedback": ""}
            except Exception as e2:
                logger.error(f"[ANALYST] Backup LLM also failed: {e2}")
        return {"messages": [AIMessage(content="I'm sorry, I encountered an error while analyzing that. Please try again.")]}


def reviewer_node(state: AgentState):
    """Reviewer node: ensures analyst output is complete and non-empty."""
    loop_count = state.get("loop_count", 0) + 1
    logger.info(f"[REVIEWER] Verifying (loop {loop_count}/{MAX_LOOPS})...")

    if loop_count >= MAX_LOOPS - 1:
        return {"next_step": END, "loop_count": loop_count}

    analyst_answer = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, AIMessage) and msg.content:
            analyst_answer = _get_text(msg.content)
            break

    if analyst_answer and len(analyst_answer.strip()) > 0:
        return {"next_step": END, "loop_count": loop_count}

    return {
        "next_step": "analyst",
        "feedback": "Your response was empty. Please provide an answer or analysis.",
        "loop_count": loop_count
    }


def tool_node(state: AgentState):
    """Executes tool calls from the Analyst concurrently using ThreadPoolExecutor."""
    last_message = state["messages"][-1]

    if not hasattr(last_message, 'tool_calls') or not last_message.tool_calls:
        return {
            "messages": [AIMessage(content="No tool calls requested.")],
            "next_step": END
        }

    def _execute_single_tool(tc):
        tool_name = tc["name"]
        tool_args = tc["args"]
        tool_call_id = tc["id"]

        logger.info(f"[TOOLS] Executing {tool_name}({tool_args})...")

        if tool_name not in tool_map:
            return ToolMessage(
                content=f"ERROR: Tool '{tool_name}' not found. Available: {list(tool_map.keys())}",
                tool_call_id=tool_call_id
            )

        try:
            res = tool_map[tool_name].invoke(tool_args)
            res_str = json.dumps(res, default=str) if not isinstance(res, str) else res
            if len(res_str) > 4000:
                res_str = res_str[:3900] + "\n... [truncated, showing first 3900 chars]"
            return ToolMessage(content=res_str, tool_call_id=tool_call_id)
        except Exception as e:
            logger.error(f"[TOOLS] Error in {tool_name}: {e}")
            return ToolMessage(content=f"ERROR executing {tool_name}: {str(e)}", tool_call_id=tool_call_id)

    # Parallelize tool execution across worker threads
    with ThreadPoolExecutor(max_workers=min(5, len(last_message.tool_calls))) as executor:
        tool_messages = list(executor.map(_execute_single_tool, last_message.tool_calls))

    return {"messages": tool_messages, "next_step": "analyst"}


def route_next(state: AgentState):
    return state.get("next_step", END)


def route_after_analyst(state: AgentState):
    last_message = state["messages"][-1]
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    return "reviewer"


# ---------------------------------------------------------------------------
# Graph Compilation
# ---------------------------------------------------------------------------

builder = StateGraph(AgentState)

builder.add_node("analyst", analyst_node)
builder.add_node("reviewer", reviewer_node)
builder.add_node("tools", tool_node)

builder.set_entry_point("analyst")

builder.add_conditional_edges("analyst", route_after_analyst, {
    "tools": "tools",
    "reviewer": "reviewer"
})

builder.add_conditional_edges("reviewer", route_next, {
    "tools": "tools",
    "analyst": "analyst",
    END: END
})

builder.add_edge("tools", "analyst")

try:
    pool = get_pool()
    with pool.connection(timeout=3) as test_conn:
        with test_conn.cursor() as cur:
            cur.execute("SELECT 1")
    saver = PostgresSaver(pool)
    graph = builder.compile(checkpointer=saver)
    logger.info("[AGENT] Graph compiled with PostgreSQL checkpointer.")
except Exception as e:
    logger.warning(f"[AGENT] PostgreSQL checkpointer unavailable ({e}), using MemorySaver fallback.")
    saver = MemorySaver()
    graph = builder.compile(checkpointer=saver)

__all__ = ["graph", "StockAnalysisResponse", "DataPoint", "saver"]
