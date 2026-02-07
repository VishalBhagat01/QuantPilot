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
    loop_count: int 

# -------------------
# Tool Map
# -------------------

tool_map = {
    # -------- FINNHUB --------
    "get_stock_price": get_stock_price,
    "get_stock_news": get_stock_news,
    "get_old_news": get_old_news,

    # -------- SEARCH --------
    "search_tool": search_tool,

    # -------- ALPHAVANTAGE --------
    "get_stock_price2": get_stock_price2,
    "get_stock_news2": get_stock_news2,
    "company_inside_news": company_inside_news,
    "top_gainers": top_gainers,
    "company_overview": company_overview,
    "annual_income_statement": annual_income_statement,
    "earning_estimate": earning_estimate,
    "future_expected_earning": future_expected_earning,
    "get_gold_silver_price": get_gold_silver_price,
}


# -------------------
# Nodes
# -------------------

def llm_node(state: AgentState):
    """
    Decides whether to use a tool or respond directly.
    """
    loop_count = state.get("loop_count", 0)
    print(f"\n>>> [AGENT] Step {loop_count + 1} | Thinking...", flush=True)
    
    if loop_count >= 5:
        print("!!! [AGENT] Max steps reached. Breaking loop.", flush=True)
        return {
            "messages": [AIMessage(content="I've analyzed the data but am having trouble getting a final answer within my step limit. Please try a simpler query.")],
            "next_step": END,
            "loop_count": loop_count 
        }

    prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are an expert stock analysis chatbot.\n\n"

     "You can call external tools to fetch live market data, fundamentals, news, earnings, and macro signals.\n\n"

     "Available tools and when to use them:\n"
     "- get_stock_price → live stock quote and price metrics\n"
     "- get_stock_news → latest company news\n"
     "- get_old_news → historical company news\n"
     "- search_tool → web search when APIs cannot answer\n"
     "- get_stock_price2 → historical daily price series\n"
     "- get_stock_news2 → news sentiment data\n"
     "- company_inside_news → earnings call transcript\n"
     "- top_gainers → today’s top gaining and losing stocks\n"
     "- company_overview → company fundamentals and valuation\n"
     "- annual_income_statement → revenue and profit data\n"
     "- earning_estimate → analyst EPS estimates\n"
     "- future_expected_earning → upcoming earnings dates\n"
     "- get_gold_silver_price → gold and silver spot prices\n\n"

     "If tool data is required, respond with ONLY valid JSON using this format:\n\n"

     "{{\"action\":\"tool\",\"tool\":\"tool_name\",\"args\":{{\"symbol\":\"TICKER\"}}}}\n\n"

     "If the tool takes no arguments, use:\n"

     "{{\"action\":\"tool\",\"tool\":\"top_gainers\",\"args\":{{}}}}\n\n"

     "Argument rules:\n"
     "- Include symbol when required\n\n"

     "Example with symbol:\n"
     "{{\"action\":\"tool\",\"tool\":\"get_stock_price\",\"args\":{{\"symbol\":\"AAPL\"}}}}\n\n"

     "Example without symbol:\n"
     "{{\"action\":\"tool\",\"tool\":\"top_gainers\",\"args\":{{}}}}\n\n"

     "Output rules:\n"
     "- JSON only when calling tools\n"
     "- No markdown\n"
     "- No explanation text\n"
     "- One tool call per message\n"
     "- Use double quotes only\n"
     "- Never include extra fields\n\n"

     "If you can answer directly without tools, respond in plain text.\n"
     "Never mix JSON and text."
    ),
    ("placeholder", "{messages}")
])

    chain = prompt | llm
    
    try:
        response = chain.invoke({"messages": state["messages"]})
        print(f">>> [AGENT] AI responds. Parsing...", flush=True)
        return {
            "messages": [response],
            "next_step": "parse",
            "loop_count": loop_count + 1 
        }
    except Exception as e:
        print(f"!!! [AGENT] LLM Error: {e}", flush=True)
        return {
            "messages": [AIMessage(content=f"Sorry, I encountered an error: {str(e)}")],
            "next_step": END,
            "loop_count": loop_count + 1
        }

def parse_node(state: AgentState):
    """
    Checks if the AI output is a tool call or a final answer.
    """
    last_message = state["messages"][-1]
    content = last_message.content.strip()
    loop_count = state.get("loop_count", 0)
    
    try:

        start_idx = content.find('{')
        end_idx = content.rfind('}')
        
        if start_idx != -1 and end_idx != -1:
            json_str = content[start_idx:end_idx+1]
            parsed = json.loads(json_str)
            
            if parsed.get("action") == "tool":
                print(f">>> [AGENT] Action: Tool -> {parsed.get('tool')}", flush=True)
                return {"next_step": "tools", "loop_count": loop_count}
        
        print(">>> [AGENT] Action: Direct Response. Ending.", flush=True)
        return {"next_step": END, "loop_count": loop_count}
    except Exception as e:
        print(f"!!! [AGENT] JSON Fix required: {e}", flush=True)
        error_msg = f"Your last response was not valid JSON: {str(e)}. Please retry with the correct JSON format if you need a tool."
        return {
            "messages": [HumanMessage(content=f"SYSTEM NOTICE: {error_msg}")],
            "next_step": "llm",
            "loop_count": loop_count
        }

def tool_node(state: AgentState):
    """
    Executes the requested tool and feeds back the result.
    """
    ai_message = next(msg for msg in reversed(state["messages"]) if isinstance(msg, AIMessage))
    content = ai_message.content.strip()
    loop_count = state.get("loop_count", 0)
    
    try:
        start_idx = content.find('{')
        end_idx = content.rfind('}')
        parsed = json.loads(content[start_idx:end_idx+1])
        
        tool_name = parsed["tool"]
        tool_args = parsed.get("args", {})
        
        print(f">>> [AGENT] Executing {tool_name} with {tool_args}", flush=True)
        
        if tool_name not in tool_map:
            raise ValueError(f"Unknown tool: {tool_name}")
            
        tool = tool_map[tool_name]
        result = tool.invoke(tool_args)
        
        result_str = str(result)[:1000] 
        print(f">>> [AGENT] Tool success. Informing AI...", flush=True)
        
        return {
            "messages": [HumanMessage(content=f"Observation from {tool_name}: {result_str}")],
            "next_step": "llm",
            "loop_count": loop_count
        }
    except Exception as e:
        print(f"!!! [AGENT] Tool Error: {e}", flush=True)
        return {
            "messages": [HumanMessage(content=f"SYSTEM ERROR: The tool failed: {str(e)}. Please adjust your request or try another tool.")],
            "next_step": "llm",
            "loop_count": loop_count
        }



# -------------------
# Router logic
# -------------------

def route_next(state: AgentState):
    return state["next_step"]

# -------------------
# Graph Construction
# -------------------

builder = StateGraph(AgentState)

builder.add_node("llm", llm_node)
builder.add_node("parse", parse_node)
builder.add_node("tools", tool_node)

builder.set_entry_point("llm")

builder.add_edge("llm", "parse")
builder.add_conditional_edges("parse", route_next, {
    "tools": "tools",
    "llm": "llm",
    END: END
})
builder.add_edge("tools", "llm")

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
