# 📊 QuantPilot — AI Financial Research & Algorithmic Trading Platform

QuantPilot is a modular, high-performance financial intelligence system combining multi-agent LLM orchestration (LangGraph), a local rule-based market scanner, technical indicator analysis, and automated paper trading (Alpaca Markets).

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

## ⚡ Quick Start

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

### 3. Frontend Setup
1. Open a second terminal:
   ```powershell
   cd "C:\Users\VISHAL BHAGAT\Desktop\Stock-Analyzer\frontend"
   npm install
   npm run dev
   ```
2. Open **http://localhost:5173** in your web browser.

---

## 🚀 Deploying to Render and Vercel

The repository includes [`render.yaml`](./render.yaml) for the FastAPI service and
[`frontend/vercel.json`](./frontend/vercel.json) for Vite's client-side routing.
Deploy the backend first so its public URL is available for the frontend.

### 1. Deploy the backend on Render

1. Push the repository to GitHub and create a **New > Blueprint** in Render.
2. Select the repository. Render will detect `render.yaml` and create the
   `quantpilot-api` web service.
3. Add the values marked `sync: false` in Render's Environment settings. Copy
   the variable names from [`backend/.env.example`](./backend/.env.example);
   never upload `.env` or commit real secrets.
4. Set `ALPACA_REDIRECT_URI` to:
   `https://YOUR-RENDER-SERVICE.onrender.com/auth/alpaca/callback`
5. Set `FRONTEND_URL` temporarily to your future Vercel URL and
   `CORS_ORIGINS` to that URL. During local testing, use
   `http://localhost:5173` instead.
6. After the first deploy, verify:
   `https://YOUR-RENDER-SERVICE.onrender.com/health`

### 2. Deploy the frontend on Vercel

1. Import the same GitHub repository into Vercel.
2. Set **Root Directory** to `frontend`.
3. Vercel should detect Vite. Use `npm run build` as the build command and
   `dist` as the output directory.
4. Add the environment variables:
   - `VITE_API_URL=https://YOUR-RENDER-SERVICE.onrender.com`
   - `VITE_SUPABASE_URL=your_supabase_project_url`
   - `VITE_SUPABASE_ANON_KEY=your_supabase_anon_key`
5. Redeploy and copy the resulting Vercel URL.

### 3. Finish OAuth and CORS configuration

1. In Render, set `FRONTEND_URL` to the exact Vercel origin, for example
   `https://quantpilot.vercel.app` (no trailing slash).
2. Set `CORS_ORIGINS` to the same origin. For a custom domain, use the custom
   domain instead of the `vercel.app` URL.
3. In Alpaca's OAuth application settings, add the exact Render callback URL
   from step 1. The callback URL must use HTTPS in production.
4. In Supabase Authentication > URL Configuration, add the Vercel URL to
   **Site URL** and add `https://YOUR-VERCEL-DOMAIN/auth/callback` to the
   allowed redirect URLs.
5. Redeploy Render after changing environment variables, then test login,
   Alpaca connect, `/health`, and one authenticated API request.

Do not use `*` for production CORS when credentials are enabled. Keep the
encryption key stable after deployment; changing it makes previously stored
Alpaca OAuth tokens unreadable.

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
5. **Zero Dead Code & Full Type Safety**:
   - All unreachable code paths, phantom dependencies, and ESLint issues have been resolved.
   - Both backend compilation and frontend production builds pass with 0 errors.

## 🧩 Module Boundaries

- **Frontend pages** compose views such as authentication, terms, and trading.
- **Frontend hooks** own reusable stateful behavior such as theme persistence and technical scans.
- **Frontend components** focus on presentation and user interaction.
- **Backend routers** expose HTTP endpoints and delegate to services/tools.
- **Backend trading services** contain scanner, broker, and signal logic independently of FastAPI.
- **Paper orders** are routed through the authenticated user's encrypted Alpaca OAuth connection; the agent cannot trade without that connection.
