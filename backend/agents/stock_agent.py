from typing import Annotated, List, TypedDict, Optional, Literal
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.checkpoint.memory import InMemorySaver
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
    get_gold_silver_price,
    get_stock_intraday_chart,

    # -------- NEW: PATTERN DETECTION (YOLOv8) --------
    # Uses foduucom/stockmarket-pattern-detection-yolov8 model
    # to detect chart patterns and generate BUY/SELL/HOLD signals
    detect_chart_patterns,

    # -------- NEW: BROKER / TRADING (Alpaca) --------
    # Connects to Alpaca Markets API for trade execution
    # Default: paper trading (sandbox, no real money)
    get_broker_account,
    get_broker_positions,
    place_trade,
    close_trade,
)
import json
import os
from dotenv import load_dotenv


load_dotenv()

# -------------------
# Constants
# -------------------
MAX_LOOPS = 6  

# -------------------
# Structured Output Schemas
# -------------------

class ReviewerDecision(BaseModel):
    """Structured decision from the Reviewer agent."""
    decision: Literal["TOOL_CALL", "CONTINUE", "FINAL", "FEEDBACK"] = Field(
        description=(
            "TOOL_CALL = analyst made valid tool calls, route to tool execution. "
            "CONTINUE = tool results received, send back to analyst for more analysis. "
            "FINAL = analyst produced a complete, accurate response. "
            "FEEDBACK = analyst response is incomplete or wrong, send feedback."
        )
    )
    feedback: Optional[str] = Field(
        default=None,
        description="Specific feedback for the analyst if decision is FEEDBACK or CONTINUE. Be precise about what is missing."
    )


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


# -------------------
# LLM Configuration
# -------------------

llm2 = ChatGoogleGenerativeAI(
    model="models/gemini-2.5-flash",
    temperature=0.1
)

llm3 = ChatGroq(
    model="moonshotai/kimi-k2-instruct-0905",
    temperature=0
)

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0
)

# -------------------
# Tools List (for binding)
# -------------------

tools_list = [
    # --- Existing market data tools ---
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
    get_gold_silver_price,
    get_stock_intraday_chart,

    # --- NEW: Pattern detection tool (YOLOv8) ---
    detect_chart_patterns,

    # --- NEW: Broker/trading tools (Alpaca) ---
    get_broker_account,
    get_broker_positions,
    place_trade,
    close_trade,
]

# Bind tools to the Analyst LLM — enables native tool calling
analyst_llm = llm.bind_tools(tools_list)

tool_map = {t.name: t for t in tools_list}

# -------------------
# State Definition
# -------------------

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    next_step: str
    feedback: str       # Reviewer feedback for the analyst
    loop_count: int     # Track iteration count to prevent infinite loops


# -------------------
# Nodes
# -------------------

def analyst_node(state: AgentState):
    """
    Analyst (Groq/Llama 3.3): Analyzes requirements and makes tool calls or produces final answers.
    Uses native tool binding — no JSON string parsing needed.
    """
    loop_count = state.get("loop_count", 0)
    print(f"\n>>> [ANALYST] Thinking... (loop {loop_count})", flush=True)

    feedback = state.get("feedback", "")

    # If we're at the loop limit, force a final answer
    force_final = loop_count >= MAX_LOOPS - 1  # Leave one last loop for reviewer to finalize

    feedback_section = f"\n\nCRITICAL FEEDBACK FROM REVIEWER:\n{feedback}" if feedback else ""
    force_section = (
        "\n\n MANDATORY: You have reached the maximum number of analysis cycles. "
        "You MUST produce your FINAL answer NOW using whatever data you already have in the messages history. "
        "Do NOT make any more tool calls. Summarize your findings and end with DASHBOARD:TICKER."
    ) if force_final else ""

    # ==================================================================
    # UPDATED PROMPT: Added Pattern Detection + Broker/Trading sections
    # ==================================================================
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
     "- get_gold_silver_price → commodity prices\n\n"

     "🆕 AI Pattern Detection (YOLOv8 Model):\n"
     "- detect_chart_patterns → runs YOLOv8 AI model on candlestick charts\n"
     "  Detects: Head & Shoulders, Double Top/Bottom, Triangle, StockLine\n"
     "  Returns: detected patterns + BUY/SELL/HOLD signal with confidence\n\n"

     "🆕 Broker & Trading (Alpaca Markets):\n"
     "- get_broker_account → check trading account balance & buying power\n"
     "- get_broker_positions → view all current stock holdings\n"
     "- place_trade → execute a BUY or SELL order (market or limit)\n"
     "- close_trade → close an entire position for a stock\n\n"

     "====================\n"
     "RULES\n"
     "====================\n"
     "1. If the user asks about ANY stock/company data → you MUST call the appropriate tool(s).\n"
     "2. You CAN call MULTIPLE tools in a single message for parallel data fetching.\n"
     "3. NEVER answer with internal knowledge when a tool exists for that data.\n"
     "4. When you have enough tool data, produce a comprehensive markdown analysis.\n"
     "5. When discussing a specific stock, end your response with: DASHBOARD:TICKER\n"
     "6. Cite which tools/data sources you used in your analysis.\n\n"

     "====================\n"
     "TRADING RULES (IMPORTANT!)\n"
     "====================\n"
     "7. When the user asks about buying/selling, ALWAYS run detect_chart_patterns FIRST.\n"
     "8. ALWAYS show the pattern detection results and trading signal BEFORE placing any trade.\n"
     "9. ALWAYS check get_broker_account to verify buying power before placing a BUY order.\n"
     "10. ALWAYS check get_broker_positions to see existing holdings before suggesting trades.\n"
     "11. NEVER place a trade without explaining the patterns and signal to the user first.\n"
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
        
        # If the LLM returned an empty response or something that looks like an error,
        # but didn't throw an exception, we catch it here.
        if isinstance(response, AIMessage) and not response.content and not response.tool_calls:
            return {"messages": [AIMessage(content="I encountered an issue processing your request. Please try again.")]}

        return {"messages": [response], "feedback": ""}  # Clear feedback once processed
    except Exception as e:
        print(f"[ERROR] Analyst LLM failed: {e}")
        return {"messages": [AIMessage(content=f"I'm sorry, I encountered a technical error while analyzing that. Please try a different query or try again later.")]}


def reviewer_node(state: AgentState):
    """
    Reviewer (Gemini 2.5 Flash): Validates Analyst output using structured decisions.
    Uses Pydantic model for deterministic routing — no keyword matching.
    """
    loop_count = state.get("loop_count", 0) + 1
    print(f">>> [REVIEWER] Verifying... (loop {loop_count}/{MAX_LOOPS})", flush=True)

    last_message = state["messages"][-1]

    # If we've exceeded the loop limit, force END
    if loop_count >= MAX_LOOPS:
        print(f">>> [REVIEWER] Loop limit reached ({MAX_LOOPS}), forcing END.", flush=True)
        return {"next_step": END, "loop_count": loop_count}

    # If the last message has tool_calls, route directly to tools (no LLM needed)
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        print(f">>> [REVIEWER] Detected {len(last_message.tool_calls)} tool call(s), routing to tools.", flush=True)
        return {"next_step": "tools", "loop_count": loop_count}

    # If the last message is a ToolMessage, route back to analyst for analysis
    if isinstance(last_message, ToolMessage):
        print(f">>> [REVIEWER] Tool result received, routing back to analyst.", flush=True)
        return {"next_step": "analyst", "loop_count": loop_count}

    # For text responses, use the structured Reviewer LLM to evaluate
    try:
        reviewer_llm = llm2.with_structured_output(ReviewerDecision)

        review_prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are the Senior Reviewer in a stock research system.\n"
             "Evaluate the analyst's latest response and decide the next step.\n\n"
             "Decision guide:\n"
             "- TOOL_CALL: The analyst wants to call tools (has tool calls in the message)\n"
             "- CONTINUE: Tool results were just received and analyst needs to analyze them\n"
             "- FINAL: The analyst produced a complete, well-sourced response with real data\n"
             "- FEEDBACK: The analyst's response is missing data, contains guesses, or is incomplete\n\n"
             "A response is FINAL if:\n"
             "1. It contains actual data from tool results (not made-up numbers)\n"
             "2. It answers the user's question adequately\n"
             "3. It includes 'DASHBOARD:TICKER' when discussing a specific stock\n\n"
             "A response needs FEEDBACK if:\n"
             "1. It contains generic advice without real data\n"
             "2. It mentions needing to check something but hasn't\n"
             "3. It appears to be hallucinating numbers not from tools"
            ),
            ("placeholder", "{messages}")
        ])

        eval_chain = review_prompt | reviewer_llm
        decision = eval_chain.invoke({"messages": state["messages"]})

        print(f">>> [REVIEWER] Decision: {decision.decision}", flush=True)
        if decision.feedback:
            print(f">>> [REVIEWER] Feedback: {decision.feedback}", flush=True)

        if decision.decision == "TOOL_CALL":
            return {"next_step": "tools", "loop_count": loop_count}
        elif decision.decision == "FEEDBACK":
            return {"next_step": "analyst", "feedback": decision.feedback, "loop_count": loop_count}
        elif decision.decision == "CONTINUE":
            return {"next_step": "analyst", "loop_count": loop_count}
        else:  # FINAL
            return {"next_step": END, "loop_count": loop_count}

    except Exception as e:
        print(f">>> [REVIEWER] Structured output failed: {e}, defaulting to END", flush=True)
        return {"next_step": END, "loop_count": loop_count}


def tool_node(state: AgentState):
    """
    Executes tool calls from the Analyst — supports PARALLEL execution.
    Reads native tool_calls from the AIMessage instead of parsing JSON strings.
    Returns ToolMessage(s) with proper tool_call_id.
    """
    last_message = state["messages"][-1]

    # Native tool calls from bind_tools
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
                # Smart truncation: prioritize structured data
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

    # Fallback: if no native tool calls found, return error
    return {
        "messages": [AIMessage(content="No tool calls found in the last message. Providing analysis with available data.")],
        "next_step": END
    }


# -------------------
# Router Logic
# -------------------

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


# -------------------
# Graph Construction
# -------------------

builder = StateGraph(AgentState)

builder.add_node("analyst", analyst_node)
builder.add_node("reviewer", reviewer_node)
builder.add_node("tools", tool_node)

builder.set_entry_point("analyst")

# Analyst → conditional: if tool calls go to tools, else go to reviewer
builder.add_conditional_edges("analyst", route_after_analyst, {
    "tools": "tools",
    "reviewer": "reviewer"
})

# Reviewer decides: tools / analyst / END
builder.add_conditional_edges("reviewer", route_next, {
    "tools": "tools",
    "analyst": "analyst",
    END: END
})

# After tools, ALWAYS go back to analyst for analysis
builder.add_edge("tools", "analyst")

# -------------------
# Database
# -------------------

saver = PostgresSaver(get_pool())

graph = builder.compile(checkpointer=saver)

__all__ = ["graph", "StockAnalysisResponse", "DataPoint"]

if __name__ == "__main__":
    config = {"configurable": {"thread_id": "1"}}
    inputs = {"messages": [HumanMessage(content="What is the price of AAPL?")], "loop_count": 0}
    for event in graph.stream(inputs, config=config):
        for value in event.values():
            print(value["messages"][-1].content if "messages" in value else value)
