from typing import Annotated, List, TypedDict, Union
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
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
)
import json
import os
from dotenv import load_dotenv


load_dotenv()

# -------------------
# LLM Configuration
# -------------------

llm2 = ChatGoogleGenerativeAI(
    model="models/gemini-2.5-flash",
    temperature=0.1
)

llm = ChatGroq(
    model="moonshotai/kimi-k2-instruct-0905",
    temperature=0
)
# -------------------
# State Definition
# -------------------

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    next_step: str
    feedback: str # Reviewer feedback for the analyst

# -------------------
# Tool Map
# -------------------

tool_map = {
    "get_stock_price": get_stock_price,
    "get_stock_news": get_stock_news,
    "get_old_news": get_old_news,
    "search_tool": search_tool,
    "get_stock_price2": get_stock_price2,
    "get_stock_news2": get_stock_news2,
    "company_inside_news": company_inside_news,
    "top_gainers": top_gainers,
    "company_overview": company_overview,
    "annual_income_statement": annual_income_statement,
    "earning_estimate": earning_estimate,
    "future_expected_earning": future_expected_earning,
    "get_gold_silver_price": get_gold_silver_price,
    "get_stock_intraday_chart": get_stock_intraday_chart,
}


# -------------------
# Nodes
# -------------------

def analyst_node(state: AgentState):
    """
    LLM1 (Groq): Analyzes requirements and proposes tool calls or answers.
    Considers feedback from the Reviewer.
    """
    print(f"\n>>> [ANALYST] Thinking...", flush=True)
    
    feedback = state.get("feedback", "")
    feedback_section = f"\n\nCRITICAL FEEDBACK FROM REVIEWER:\n{feedback}" if feedback else ""

    prompt = ChatPromptTemplate.from_messages([
    ("system",
    "You are the Lead Analyst in a multi-agent stock research system.\n"
    "You NEVER guess market data. You ALWAYS use tools when data is required.\n"
    "You are a decision router + analyst.\n\n"

    "====================\n"
    "AVAILABLE TOOLS\n"
    "====================\n"
    "Price & Market Data:\n"
    "- get_stock_price → real-time quote\n"
    "- get_stock_price2 → latest daily OHLCV\n"
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

    "====================\n"
    "MANDATORY TOOL RULES\n"
    "====================\n"
    "1. If the user asks about ANY stock/company data → you MUST call a tool.\n"
    "2. If price is requested → call get_stock_price.\n"
    "3. If chart/price movement is requested → call get_stock_intraday_chart.\n"
    "4. If fundamentals/valuation is requested → call company_overview.\n"
    "5. If news/sentiment is requested → call a news tool.\n"
    "6. If unknown info is requested → call search_tool and analyze the output from the tools than return it to the user after formatting it.\n"
    "7. NEVER answer with internal knowledge when a tool exists but you must format the given tool data as the user aksed.\n"
    "8  if required call as many tool as need per message.\n"
    "9. NEVER explain tool calls.\n"
    "10. Tool calls MUST be valid JSON ONLY.\n\n"

    "====================\n"
    "TOOL CALL FORMAT\n"
    "====================\n"
    "{\"action\":\"tool\",\"tool\":\"TOOL_NAME\",\"args\":{\"symbol\":\"TICKER\"}}\n\n"

    "No markdown. No commentary. No extra keys.\n\n"

    "====================\n"
    "DIRECT RESPONSE RULES\n"
    "====================\n"
    "If sufficient tool data has already been provided in prior messages:\n"
    "- Respond in plain text analysis\n"
    "- When discussing a stock → append on new line: DASHBOARD:TICKER\n\n"

    f"{feedback_section}"
    ),
    ("placeholder", "{messages}")
])


    chain = prompt | llm
    try:
        response = chain.invoke({"messages": state["messages"]})
        return {"messages": [response], "feedback": ""} # Clear feedback once processed
    except Exception as e:
        return {"messages": [AIMessage(content=f"Analyst encountered error: {str(e)}")]}

def reviewer_node(state: AgentState):
    """
    LLM2 (Gemini): Validates Analyst output and tool results.
    Decides if the task is done or needs more work.
    """
    print(f">>> [REVIEWER] Verifying...", flush=True)
    
    last_message = state["messages"][-1]
    
    # Reviewer's prompt to evaluate the state
    review_prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are the Senior Reviewer. Your goal is to ensure the Analyst correctly answers the user's question with high accuracy.\n\n"
         "Evaluate the last message/state:\n"
         "1. If it's a JSON tool call: Is it valid JSON? Does it use the correct symbol? (Mark as 'VALID_TOOL' or 'INVALID_TOOL')\n"
         "2. If it's a Tool result: Did it fail? Does it need more context? (Mark as 'CONTINUE' or 'RETRY')\n"
         "3. If it's a draft response: Is it complete? Does it include 'DASHBOARD:TICKER'? (Mark as 'FINAL' or 'FEEDBACK')\n\n"
         "Respond with a decision and any feedback for the Analyst if needed."
        ),
        ("placeholder", "{messages}")
    ])
    
    # We use llm2 for reasoning here
    eval_chain = review_prompt | llm2
    eval_res = eval_chain.invoke({"messages": state["messages"]})
    eval_content = eval_res.content.upper()
    
    # Determine next step
    if "VALID_TOOL" in eval_content:
        return {"next_step": "tools"}
    elif "INVALID_TOOL" in eval_content or "FEEDBACK" in eval_content or "RETRY" in eval_content:
        return {"next_step": "analyst", "feedback": eval_res.content}
    elif "FINAL" in eval_content or "DASHBOARD:" in last_message.content:
        return {"next_step": END}
    elif "CONTINUE" in eval_content:
        return {"next_step": "analyst"}
    
    # Fallback: If it looks like a tool call but not explicit, try tools
    if "{" in last_message.content and "action" in last_message.content:
        return {"next_step": "tools"}
        
    return {"next_step": END}

def tool_node(state: AgentState):
    """Executes tools requested by Analyst."""
    last_message = state["messages"][-1]
    content = last_message.content.strip()
    
    try:
        start_idx = content.find('{')
        end_idx = content.rfind('}')
        parsed = json.loads(content[start_idx:end_idx+1])
        
        tool_name = parsed["tool"]
        tool_args = parsed.get("args", {})
        
        print(f">>> [TOOLS] Executing {tool_name}...", flush=True)
        
        if tool_name not in tool_map:
            return {"messages": [HumanMessage(content=f"SYSTEM ERROR: Tool '{tool_name}' unknown.")]}
            
        result = tool_map[tool_name].invoke(tool_args)
        return {"messages": [HumanMessage(content=f"Observation from {tool_name}: {str(result)[:2000]}")], "next_step": "analyst"}
    except Exception as e:
        return {"messages": [HumanMessage(content=f"SYSTEM ERROR: JSON/Tool failure: {str(e)}")], "next_step": "analyst"}

# -------------------
# Router logic
# -------------------

def route_next(state: AgentState):
    return state.get("next_step", END)

# -------------------
# Graph Construction
# -------------------

builder = StateGraph(AgentState)

builder.add_node("analyst", analyst_node)
builder.add_node("reviewer", reviewer_node)
builder.add_node("tools", tool_node)

builder.set_entry_point("analyst")

builder.add_edge("analyst", "reviewer")

builder.add_conditional_edges("reviewer", route_next, {
    "tools": "tools",
    "analyst": "analyst",
    END: END
})

builder.add_edge("tools", "analyst")

#-----------------------------
#  DataBase
#----------------------------

saver = PostgresSaver(get_pool())

graph = builder.compile(checkpointer=saver)

__all__ = ["graph"]

if __name__ == "__main__":
    config = {"configurable": {"thread_id": "1"}}
    inputs = {"messages": [HumanMessage(content="What is the price of AAPL?")]}
    for event in graph.stream(inputs, config=config):
        for value in event.values():
            print(value["messages"][-1].content if "messages" in value else value)
