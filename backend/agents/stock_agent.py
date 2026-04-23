from typing import Annotated, List, TypedDict, Optional, Literal
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint  # noqa: F401 (disabled, kept for local dev)
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.checkpoint.postgres import PostgresSaver
from pydantic import BaseModel, Field
from backend.db.db import get_pool
from backend.ingestion.tool import (
    # -------- FINNHUB --------
    get_stock_price,
    get_stock_news,
    get_old_news,

    # -------- SEARCH --------
    search_tool,

    # -------- ALPHAVANTAGE --------
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

    # Default: paper trading (sandbox, no real money)
    get_broker_account,
    get_broker_positions,
    place_trade,
    close_trade,
)
import json
from dotenv import load_dotenv


load_dotenv()

MAX_LOOPS = 3


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


llm = ChatGoogleGenerativeAI(
    model="models/gemini-2.5-flash",
    temperature=0.1
)

llm2 = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0
)

llm3 = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0
)

# HuggingFace model disabled — not used in graph, blocks startup on Render
# llm_hf = ChatHuggingFace(
#     llm=HuggingFaceEndpoint(
#         repo_id="mistralai/Mistral-7B-Instruct-v0.3",
#         task="text-generation",
#         max_new_tokens=1024,
#         do_sample=False,
#     )
# )


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

analyst_llm = llm2.bind_tools(tools_list)

tool_map = {t.name: t for t in tools_list}

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    next_step: str
    feedback: str       # Reviewer feedback for the analyst
    loop_count: int     # Track iteration count to prevent infinite loops


def analyst_node(state: AgentState):
    """
    Analyst (Groq/Llama 3.3): Analyzes requirements and makes tool calls or produces final answers.
    Uses native tool binding — no JSON string parsing needed.
    """
    loop_count = state.get("loop_count", 0)
    print(f"\n>>> [ANALYST] Thinking... (loop {loop_count})", flush=True)

    feedback = state.get("feedback", "")

    # If we're at the loop limit, force a final answer
    force_final = loop_count >= MAX_LOOPS - 1

    feedback_section = f"\n\nCRITICAL FEEDBACK FROM REVIEWER:\n{feedback}" if feedback else ""
    force_section = (
        "\n\n MANDATORY: You have reached the maximum number of analysis cycles. "
        "You MUST produce your FINAL answer NOW using whatever data you already have in the messages history. "
        "Do NOT make any more tool calls. Summarize your findings and end with DASHBOARD:TICKER."
    ) if force_final else ""


    prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are the Lead Analyst in a multi-agent stock research & trading system.\n"
     "You NEVER guess market data. You ALWAYS use tools when data is required.\n\n"

     "====================\n"
     "AVAILABLE TOOLS\n"
     "====================\n"
     "Price & Market Data:\n"
     "- get_stock_price → real-time quote (Finnhub)\n"
     "- get_stock_price2 → latest daily OHLCV (AlphaVantage)\n"
     "- get_stock_intraday_chart → intraday chart series\n"
     "- top_gainers → market movers\n\n"

     "News & Sentiment:\n"
     "- get_stock_news → recent company news\n"
     "- get_old_news → historical news\n"
     "- get_stock_news2 → sentiment scored news\n"
     "- search_tool → general web search\n\n"

     "Fundamentals & Financials:\n"
     "- company_overview → fundamentals + valuation\n"
     "- annual_income_statement → financial reports\n"
     "- earning_estimate → analyst projections\n"
     "- future_expected_earning → earnings calendar\n"
     "- company_inside_news → earnings transcripts\n\n"

     "Macro:\n"
     "- get_gold_price → current gold spot price (XAU/USD)\n"
     "- get_silver_price → current silver spot price (XAG/USD)\n\n"

     "🆕 Trading Signal Prediction (Simple Technical Analysis):\n"
     "- predict_stock_signal → analyzes stock data for buy/sell/hold recommendations\n"
     "  Indicators: SMA-20, SMA-50, RSI, MACD\n"
     "  Returns: BUY/SELL/HOLD signal + confidence + indicator values\n\n"

     "🆕 Broker & Trading (Alpaca Markets):\n"
     "- get_broker_account → check trading account balance & buying power\n"
     "- get_broker_positions → view all current stock holdings\n"
     "- place_trade → execute a BUY or SELL order (market or limit)\n"
     "- close_trade → close an entire position for a stock\n\n"

     "====================\n"
     "RULES\n"
     "====================\n"
     "1. If the user asks about ANY stock or commodity (gold, silver, etc.) → you MUST call the appropriate tool(s).\n"
     "2. You CAN call MULTIPLE tools in a single message for parallel data fetching.\n"
     "3. NEVER answer with internal knowledge when a tool exists for that data. ALWAYS check current prices.\n"
     "4. When you have enough tool data, produce a comprehensive markdown analysis.\n"
     "5. When discussing a specific stock, end your response with: DASHBOARD:TICKER\n"
     "6. Cite which tools/data sources you used in your analysis.\n\n"

     "====================\n"
     "TRADING RULES (IMPORTANT!)\n"
     "====================\n"
     "7. When the user asks about buying/selling, ALWAYS run predict_stock_signal FIRST.\n"
     "8. ALWAYS show the technical indicators and trading signal BEFORE placing any trade.\n"
     "9. ALWAYS check get_broker_account to verify buying power before placing a BUY order.\n"
     "10. ALWAYS check get_broker_positions to see existing holdings before suggesting trades.\n"
     "11. NEVER place a trade without explaining the technical analysis and signal to the user first.\n"
     "12. If the signal is HOLD, advise waiting — do NOT force a trade.\n"
     "13. Maximum 100 shares per trade. Paper trading is default.\n"
     f"{feedback_section}"
     f"{force_section}"
    ),
    ("placeholder", "{messages}")
    ])

    chain = prompt | analyst_llm
    try:
        response = chain.invoke({"messages": state["messages"]})
        
        if isinstance(response, AIMessage) and not response.content and not response.tool_calls:
            return {"messages": [AIMessage(content="I encountered an issue processing your request. Please try again.")]}

        return {"messages": [response], "feedback": ""}
    except Exception as e:
        print(f"[ERROR] Analyst LLM failed: {e}")
        return {"messages": [AIMessage(content=f"I'm sorry, I encountered a technical error while analyzing that. Please try a different query or try again later.")]}


def reviewer_node(state: AgentState):
    """
    Reviewer: Validates Analyst output using structured decisions.
    Only receives the user query + analyst's final text to minimise tokens.
    Auto-passes on the last allowed loop to guarantee a response is returned.
    """
    loop_count = state.get("loop_count", 0) + 1
    print(f">>> [REVIEWER] Verifying... (loop {loop_count}/{MAX_LOOPS})", flush=True)

    # ── Safety: always end on the second+ review cycle ────────────────
    if loop_count >= MAX_LOOPS - 1:
        print(">>> [REVIEWER] Max loops reached — auto-PASS", flush=True)
        return {"next_step": END, "loop_count": loop_count}

    # ── Extract only what the reviewer needs ──────────────────────────
    user_query = ""
    analyst_answer = ""
    for msg in state["messages"]:
        if isinstance(msg, HumanMessage) and not user_query:
            user_query = msg.content
        if isinstance(msg, AIMessage) and msg.content:
            analyst_answer = msg.content

    # If the analyst already produced a substantial response, lean toward PASS
    if not analyst_answer or len(analyst_answer.strip()) < 30:
        # Response is basically empty — give the analyst one more shot
        return {
            "next_step": "analyst",
            "feedback": "Your response was empty or too short. Produce a full analysis with the data you have.",
            "loop_count": loop_count
        }

    review_messages = [
        HumanMessage(content=f"USER QUERY: {user_query}"),
        AIMessage(content=f"ANALYST RESPONSE:\n{analyst_answer}"),
    ]

    prompt = ChatPromptTemplate.from_messages([
        ("system", 
         "You are the Quality Reviewer for a stock analysis agent.\n"
         "Below you will see the USER QUERY and the ANALYST RESPONSE.\n"
         "Decide PASS or FAIL.\n\n"
         "DEFAULT TO PASS. Only FAIL if the response is truly inadequate.\n\n"
         "PASS if:\n"
         "- The analyst provided any real data addressing the query.\n"
         "- Some tools may have failed — that's OK if the analyst used the data it got.\n\n"
         "FAIL only if:\n"
         "- The response is completely empty or a generic error message.\n"
         "- The analyst clearly fabricated numbers with no tool data.\n\n"
         "If FAIL, provide concise feedback."
        ),
        ("placeholder", "{messages}")
    ])

    try:
        reviewer_chain = prompt | llm2.with_structured_output(ReviewerDecision)
        response = reviewer_chain.invoke({"messages": review_messages})
        
        print(f">>> [REVIEWER] Decision: {response.status}", flush=True)

        if response.status == "FAIL":
            return {
                "next_step": "analyst", 
                "feedback": response.feedback or "Missing information.", 
                "loop_count": loop_count
            }
        
        return {"next_step": END, "loop_count": loop_count}

    except Exception as e:
        print(f">>> [REVIEWER] Error: {e}, defaulting to END", flush=True)
        return {"next_step": END, "loop_count": loop_count}


def tool_node(state: AgentState):
    """
    Executes tool calls from the Analyst — supports PARALLEL execution.
    Reads native tool_calls from the AIMessage instead of parsing JSON strings.
    Returns ToolMessage(s) with proper tool_call_id.
    """
    last_message = state["messages"][-1]

    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        tool_messages = []

        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_call_id = tool_call["id"]

            print(f">>> [TOOLS] Executing {tool_name}({tool_args})...", flush=True)

            if tool_name not in tool_map:
                tool_messages.append(ToolMessage(
                    content=f"ERROR: Tool '{tool_name}' not found. Available: {list(tool_map.keys())}",
                    tool_call_id=tool_call_id
                ))
                continue

            try:
                result = tool_map[tool_name].invoke(tool_args)
                result_str = json.dumps(result, default=str) if not isinstance(result, str) else result
                if len(result_str) > 4000:
                    result_str = result_str[:3900] + "\n... [truncated, showing first 3900 chars]"

                tool_messages.append(ToolMessage(
                    content=result_str,
                    tool_call_id=tool_call_id
                ))
                print(f">>> [TOOLS] {tool_name} returned {len(result_str)} chars", flush=True)
            except Exception as e:
                tool_messages.append(ToolMessage(
                    content=f"ERROR executing {tool_name}: {str(e)}",
                    tool_call_id=tool_call_id
                ))

        return {"messages": tool_messages, "next_step": "analyst"}

    return {
        "messages": [AIMessage(content="No tool calls found in the last message. Providing analysis with available data.")],
        "next_step": END
    }

def route_next(state: AgentState):
    return state.get("next_step", END)


def route_after_analyst(state: AgentState):
    """
    After the analyst, check if the response has tool_calls.
    If yes, skip the reviewer and go directly to tools (optimization).
    Otherwise, go to reviewer for evaluation.
    """
    last_message = state["messages"][-1]
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    return "reviewer"


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
    saver = PostgresSaver(get_pool())
    graph = builder.compile(checkpointer=saver)
    print("[AGENT] Graph compiled with PostgreSQL checkpointer.")
except Exception as e:
    print(f"[AGENT] WARNING: DB checkpointer failed ({e}), running without persistence.")
    saver = None
    graph = builder.compile()

__all__ = ["graph", "StockAnalysisResponse", "DataPoint", "saver"]

if __name__ == "__main__":
    config = {"configurable": {"thread_id": "1"}}
    inputs = {"messages": [HumanMessage(content="What is the price of AAPL?")], "loop_count": 0}
    for event in graph.stream(inputs, config=config):
        for value in event.values():
            print(value["messages"][-1].content if "messages" in value else value)
