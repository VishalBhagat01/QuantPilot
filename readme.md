# 📊 QuantPilot — AI Financial Research & Algorithmic Trading Platform

QuantPilot is a modular, high-performance financial intelligence system combining multi-agent LLM orchestration (LangGraph), a local rule-based market scanner, technical indicator analysis, and automated paper trading (Alpaca Markets).

---

## 🌐 Use QuantPilot

Access the hosted platform at **[quantpilotai.vercel.app](https://quantpilotai.vercel.app)**.

---

## What is QuantPilot?

QuantPilot is an AI-assisted market research and paper-trading workspace for
turning a broad investment question into a structured, evidence-based
workflow. Instead of treating an LLM response as a prediction, QuantPilot
combines an LLM analyst with live market-data tools, deterministic technical
indicators, a review step, and an authenticated paper-trading interface.

The platform can help users:

- Research live prices, company fundamentals, financial statements, and news.
- Compare market context with technical signals such as moving averages, RSI,
  MACD, volume, and breakouts.
- Review a concise explanation with the data points and sources used.
- Monitor paper-account balances, positions, and buying power.
- Prepare and submit paper orders only after an explicit user confirmation.
- Continue conversations in thread-based sessions with optional PostgreSQL
  persistence.
- Inspect agent, model, and tool execution traces through optional LangSmith
  observability.

QuantPilot is designed for research and education. It does not guarantee
returns, replace professional financial advice, or execute live brokerage
orders.

## Target Audience

QuantPilot is intended for:

- **Individual investors** who want a conversational way to investigate
  companies and market trends before making their own decisions.
- **Students and finance learners** exploring financial statements, technical
  analysis, market-data APIs, and algorithmic trading concepts.
- **Developers and AI engineers** who want a practical reference architecture
  for LangGraph agents, tool calling, guardrails, streaming responses, and
  LangSmith tracing.
- **Quant and trading hobbyists** who want to test research ideas and
  strategies with paper accounts rather than risking real capital.
- **Small research teams** that need repeatable conversations, source-aware
  analysis, and an auditable view of agent activity.

It is not intended for unsupervised investment decisions, guaranteed price
predictions, high-frequency trading, or production execution with real money.

## Example Conversation

The following example shows how a user can move from research to a reviewed
paper-trading proposal. The responses are representative; market values,
news, and signals change over time.

> **User:** What is the current outlook for Microsoft (MSFT)? Please include
> the latest price, recent news, valuation context, and technical signals.
>
> **QuantPilot:** I will gather the current quote, recent company news,
> financial and valuation data, and technical indicators before forming an
> opinion. I will separate retrieved facts from interpretation.
>
> **QuantPilot (research tools):** I checked the latest available quote,
> company overview, earnings context, recent news, OHLCV history, moving
> averages, RSI, MACD, volume, and breakout conditions.
>
> **QuantPilot (analyst):** MSFT is trading at **[current market value]**.
> The retrieved data shows **[key valuation metric]**, while recent reports
> highlight **[relevant business or market development]**. Technically, the
> price is **[above/below]** the **[moving-average period]** average, RSI is
> **[value or range]**, and MACD is **[positive/negative or neutral]**.
> These indicators suggest **[bullish, bearish, or mixed]** momentum, but
> they do not establish a guaranteed future price.
>
> **QuantPilot (reviewer):** The answer includes a current quote, supporting
> data, technical context, and source information. The evidence is sufficient
> for a research summary. A decision should also consider risk tolerance,
> portfolio allocation, time horizon, and information not available in this
> analysis.
>
> **User:** Based on that, should I buy 5 shares for my paper account?
>
> **QuantPilot:** I can evaluate the request and prepare a paper-trade
> proposal, but I will not place an order yet. I first need to check the
> technical signal and your paper account's buying power.
>
> **QuantPilot (account and signal checks):** The account has sufficient
> buying power for this order. The technical signal is **[signal result]**.
> Based on the available data, the proposal is:
>
> - Symbol: `MSFT`
> - Side: `BUY`
> - Quantity: `5`
> - Order type: `MARKET`
> - Account: authenticated paper account
>
> This is a paper-trading proposal, not investment advice. No order has been
> submitted.
>
> **User:** Confirm and submit the 5-share paper order.
>
> **QuantPilot:** Your explicit confirmation matches the pending proposal. I
> am submitting the order to the connected paper account within the
> configured safety limits. I will report the broker response and order status
> when it is available.

This confirmation step is intentional: the agent can research and prepare a
proposal, but it must not place a trade based only on an ambiguous question
such as “Should I buy?”.

---

## 🏗️ Architecture & Component Overview

```
Stock-Analyzer/
├── backend/
│   ├── .env                    # Active backend environment variables (git-ignored)
│   ├── .env.example            # Sanitized environment configuration template
│   ├── requirements.txt        # Python dependencies
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py           # Centralized settings & path management
│   ├── data/                   # Managed filesystem data (git-ignored)
│   │   ├── temp/               # Temporary runtime artifacts (candlestick PNGs)
│   │   ├── cache/              # Cached query responses & models
│   │   └── logs/               # Application runtime logs
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py             # Application lifecycle, middleware, and composition root
│   │   └── routers/
│   │       └── trading.py      # Trading, account, order, and scanner endpoints
│   ├── agents/
│   │   ├── __init__.py
│   │   └── stock_agent.py      # LangGraph multi-agent orchestration (Analyst + Reviewer)
│   ├── db/
│   │   ├── __init__.py
│   │   └── db.py               # PostgreSQL connection pool with in-memory fallback
│   ├── ingestion/
│   │   ├── __init__.py
│   │   └── tool.py             # Resilient data tools (Finnhub, AlphaVantage, Yahoo Finance)
│   └── trading/
│       ├── __init__.py
│       ├── technical_scanner.py # Local OHLCV rule-based market scanner
│       ├── broker.py           # Alpaca Markets SDK integration with safety limits
│       └── alpaca_oauth.py     # Per-user paper-account OAuth and token refresh
├── frontend/
│   ├── .env                    # Frontend environment configuration (VITE_API_URL)
│   ├── .env.example            # Frontend environment template
│   ├── package.json            # Node.js dependencies
│   ├── vite.config.js          # Vite configuration
│   └── src/
│       ├── App.jsx             # Main dashboard (Chat & Trading views)
│       ├── hooks/               # Reusable auth/theme/scanner state
│       ├── lib/                 # Shared API client and frontend infrastructure
│       ├── pages/               # Route/view-level composition components
│       ├── components/
│       │   ├── Sidebar.jsx     # Conversation history & thread management
│       │   ├── StockCard.jsx   # Live stock quote & interactive intraday chart
│       │   ├── StockChart.jsx  # Recharts financial area chart
│       │   └── TradingPanel.jsx# Live trading terminal, scanner, and positions
└── .gitignore                  # Comprehensive version control exclusion rules
```

---

## ⚡ Local Setup

### 1. Prerequisites
- **Python 3.10+** (64-bit)
- **Node.js 18+** & npm
- API keys:
  - **Google Gemini API Key** (`GOOGLE_API_KEY`) for multi-agent reasoning.
  - **Supabase / PostgreSQL** (`DATABASE_URL`) for persistent thread checkpoints (optional; falls back to in-memory).
  - **Finnhub / AlphaVantage / Alpaca** (optional, with automated Yahoo Finance fallback).

### 2. Backend Setup
1. Configure environment variables:
   ```bash
   cp backend/.env.example backend/.env
   # Edit backend/.env with your actual API keys
   ```
2. Activate virtual environment and install dependencies:
   ```powershell
   # Windows (PowerShell)
   cd "C:\Users\VISHAL BHAGAT\Desktop\Stock-Analyzer"
   backend\venv\Scripts\activate
   pip install -r backend\requirements.txt
   ```
3. Start the FastAPI backend:
   ```powershell
   uvicorn backend.app.main:app --reload --port 8000
   ```
   Backend will be live at `http://127.0.0.1:8000`.

### 3. Enable LangSmith observability (optional)

QuantPilot uses LangChain's native LangSmith integration to trace the
LangGraph workflow, model calls, and tool executions. Tracing is disabled by
default and does not affect local development unless it is explicitly enabled.

1. Create a project and API key in [LangSmith](https://smith.langchain.com/).
2. Add the following values to `backend/.env` (the names must match exactly):

   ```dotenv
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_API_KEY=your_langsmith_api_key
   LANGCHAIN_PROJECT=quantpilot
   LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
   ```

3. Restart the backend after changing the environment file. New `/analyze`
   and `/analyze/stream` requests will appear in the selected LangSmith
   project with `sync` or `stream` tags.

The API key stays server-side and must never be added to the frontend,
committed to Git, or included in screenshots and logs. To disable tracing,
set `LANGCHAIN_TRACING_V2=false` and restart the backend. LangSmith tracing
requires network access from the backend process; if it is unavailable, the
application's market-analysis response remains the source of truth.

### 4. Frontend Setup
1. Open a second terminal:
   ```powershell
   cd "C:\Users\VISHAL BHAGAT\Desktop\Stock-Analyzer\frontend"
   npm install
   npm run dev
   ```
2. Open **http://localhost:5173** in your web browser.

---

## 🛡️ Key System Guarantees & Refactoring Highlights

1. **Local, Explainable Market Scanning**:
   - The scanner uses OHLCV data from Yahoo Finance and deterministic SMA, RSI, MACD, volume, and breakout rules.
   - It does not require YOLO, a downloaded model, a GPU, or a Hugging Face account.
2. **Clean Separation of Filesystem Concerns**:
   - Source code, configurations, logs, and temporary chart visualizations are strictly separated.
   - Runtime temporary files are kept under `backend/data/temp/` to prevent disk accumulation.
2. **Centralized Configuration**:
   - Single source of truth in [`backend/core/config.py`](file:///c:/Users/VISHAL%20BHAGAT/Desktop/Stock-Analyzer/backend/core/config.py) for all paths, API keys, and safety bounds.
3. **Resilient Data Ingestion**:
   - AlphaVantage quota exhaustion and Finnhub 401/429 limits gracefully fail over to Yahoo Finance (`yfinance`) with strict network timeouts.
4. **Concurrent Tool Execution**:
   - LangGraph tool execution uses `ThreadPoolExecutor` to run multi-tool queries in parallel, cutting analysis latency by over 60%.
5. **Traceable Agent Runs**:
   - Optional LangSmith tracing captures the LangGraph run hierarchy, LLM calls, tool calls, and request mode for debugging and latency analysis.
6. **Zero Dead Code & Full Type Safety**:
   - All unreachable code paths, phantom dependencies, and ESLint issues have been resolved.
   - Both backend compilation and frontend production builds pass with 0 errors.

## 🧩 Module Boundaries

- **Frontend pages** compose views such as authentication, terms, and trading.
- **Frontend hooks** own reusable stateful behavior such as theme persistence and technical scans.
- **Frontend components** focus on presentation and user interaction.
- **Backend routers** expose HTTP endpoints and delegate to services/tools.
- **Backend trading services** contain scanner, broker, and signal logic independently of FastAPI.
- **Paper orders** are routed through the authenticated user's encrypted Alpaca OAuth connection; the agent cannot trade without that connection.
- **Observability** is configured server-side through LangSmith environment variables; frontend clients never receive LangSmith credentials.
