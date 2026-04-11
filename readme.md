# 📊 QuantPilot — AI Stock Analyzer & Trading Agent

> A multi-agent stock research & trading system powered by **LangGraph**, **YOLOv8 chart pattern detection**, and **Alpaca broker integration**.

---

## 🚀 What It Does

QuantPilot is an AI-powered stock analysis platform that combines:

| Feature | Description |
|---------|-------------|
| 🤖 **AI Chat Agent** | Ask natural language questions about stocks — the agent fetches real data using tools, never guesses |
| 🔍 **YOLOv8 Pattern Detection** | Detects chart patterns (Head & Shoulders, Double Top/Bottom, Triangles) from candlestick charts using the `foduucom/stockmarket-pattern-detection-yolov8` model |
| 📈 **BUY/SELL/HOLD Signals** | Converts detected patterns into actionable trading signals with confidence scores |
| 💰 **Alpaca Broker** | Executes trades via Alpaca Markets API (paper trading by default — no real money) |
| 📊 **Trading Dashboard** | Frontend panel for scanning patterns, viewing positions, and tracking orders |
| 🧠 **Multi-Agent Architecture** | Analyst + Reviewer agents with tool-calling loop for accurate, data-backed responses |

---

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────────────────────────────────┐
│   React + Vite  │     │              FastAPI Backend                 │
│   Frontend      │────▶│                                              │
│                 │     │  ┌──────────┐    ┌──────────┐   ┌─────────┐ │
│  • Chat View    │     │  │ Analyst  │◀──▶│ Reviewer │──▶│  Tools  │ │
│  • Trading View │     │  │ (Groq)   │    │ (Gemini) │   │ 19 tools│ │
│                 │     │  └──────────┘    └──────────┘   └─────────┘ │
│                 │     │       │                              │       │
│                 │     │  ┌────▼──────────────────────────────▼────┐  │
│                 │     │  │           Tool Categories              │  │
│                 │     │  │  • Finnhub (price, news)               │  │
│                 │     │  │  • AlphaVantage (fundamentals)         │  │
│                 │     │  │  • YOLOv8 (pattern detection) ← NEW   │  │
│                 │     │  │  • Alpaca (broker/trading)    ← NEW   │  │
│                 │     │  │  • DuckDuckGo (web search)            │  │
│                 │     │  └───────────────────────────────────────┘  │
│                 │     │                                              │
│                 │     │  ┌────────────────────────────────────────┐  │
│                 │     │  │  PostgreSQL (Supabase)                 │  │
│                 │     │  │  • LangGraph checkpoints               │  │
│                 │     │  │  • Thread history                      │  │
│                 │     │  └────────────────────────────────────────┘  │
└─────────────────┘     └──────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
Stock-Analyzer/
├── .env                          # API keys (Groq, Google, Finnhub, AlphaVantage, Alpaca)
├── requirements.txt              # Python dependencies
├── readme.md                     # This file
│
├── backend/
│   ├── __init__.py
│   ├── agents/
│   │   └── stock_agent.py        # LangGraph multi-agent (Analyst + Reviewer + Tools)
│   ├── app/
│   │   └── main.py               # FastAPI server with all REST endpoints
│   ├── db/
│   │   └── db.py                 # PostgreSQL connection pool (Supabase)
│   ├── ingestion/
│   │   └── tool.py               # All 19 LangChain tools (data + patterns + broker)
│   ├── pattern_detection/        # ← NEW
│   │   ├── __init__.py
│   │   └── pattern_detector.py   # YOLOv8 model loading, chart generation, inference
│   └── trading/                  # ← NEW
│       ├── __init__.py
│       ├── signal_engine.py      # Pattern → BUY/SELL/HOLD signal conversion
│       └── broker.py             # Alpaca Markets API integration
│
└── frontend/
    └── frontend/
        ├── package.json
        ├── vite.config.js
        └── src/
            ├── App.jsx           # Main app with Chat/Trading view toggle
            ├── App.css
            ├── index.css
            ├── main.jsx
            └── components/
                ├── Sidebar.jsx       # Thread list sidebar
                ├── StockCard.jsx     # Stock dashboard widget
                ├── StockChart.jsx    # Intraday price chart
                └── TradingPanel.jsx  # ← NEW: Pattern scanner + broker dashboard
```

---

## ⚙️ Prerequisites

Before running the project, make sure you have:

- **Python 3.10+** — [Download](https://www.python.org/downloads/)
- **Node.js 18+** — [Download](https://nodejs.org/)
- **Git** — [Download](https://git-scm.com/)

### API Keys Needed

| Service | Purpose | Get Key |
|---------|---------|---------|
| **Groq** | LLM for Analyst agent | [console.groq.com](https://console.groq.com) |
| **Google AI** | LLM for Reviewer agent (Gemini) | [aistudio.google.com](https://aistudio.google.com) |
| **Finnhub** | Real-time stock quotes & news | [finnhub.io](https://finnhub.io) |
| **AlphaVantage** | Fundamentals, earnings, financials | [alphavantage.co](https://www.alphavantage.co/support/#api-key) |
| **HuggingFace** | YOLOv8 model download | [huggingface.co](https://huggingface.co/settings/tokens) |
| **Alpaca** *(optional)* | Broker for trade execution | [alpaca.markets](https://alpaca.markets) |
| **Supabase** | PostgreSQL database | [supabase.com](https://supabase.com) |

---

## 🏃 How to Run

### Step 1: Clone the Project

```bash
git clone https://github.com/VishalBhagat01/QuantPilot.git
cd Stock-Analyzer
```

### Step 2: Set Up the Backend

```bash
# Create a Python virtual environment
python -m venv venv

# Activate it (Windows)
venv\Scripts\activate

# Activate it (Mac/Linux)
# source venv/bin/activate

# Install all Python dependencies
pip install -r requirements.txt
```

### Step 3: Configure API Keys

Edit the `.env` file in the project root with your actual API keys:

```env
GROQ_API_KEY=your_groq_key_here
GOOGLE_API_KEY=your_google_key_here
HUGGINGFACEHUB_API_TOKEN=your_hf_token_here
DATABASE_URL=postgresql://user:password@host:5432/dbname
FINNHUB_API_KEY=your_finnhub_key_here
ALPHAADVANTAGE_API_KEY=your_alphavantage_key_here

# Alpaca Broker (optional — for trade execution)
ALPACA_API_KEY=your_alpaca_key_here
ALPACA_SECRET_KEY=your_alpaca_secret_here
ALPACA_PAPER=true
```

> **Note:** If you don't have Alpaca keys, the chat agent and pattern scanner will still work — only the trade execution features will be unavailable.

### Step 4: Start the Backend Server

```bash
# From the project root directory
uvicorn backend.app.main:app --reload --port 8000
```

You should see:
```
[DB] Threads table initialized.
[DB] PostgresSaver tables ensured.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### Step 5: Set Up & Start the Frontend

Open a **new terminal** (keep the backend running):

```bash
# Navigate to the frontend directory
cd frontend

# Install Node.js dependencies
npm install

# Start the development server
npm run dev
```

You should see:
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
```

### Step 6: Open the App

Open your browser and go to: **http://localhost:5173**

---

## 🎯 How to Use

### 💬 Chat Mode (Default)

Ask the AI agent questions like:
- *"What is the price of AAPL?"*
- *"Analyze Tesla stock"*
- *"Compare MSFT and GOOGL fundamentals"*
- *"Detect chart patterns for NVDA"* ← Uses YOLOv8!
- *"Should I buy AAPL? Check patterns and place a trade"* ← Full pipeline!

The agent will:
1. Call the appropriate tools (Finnhub, AlphaVantage, YOLOv8, Alpaca)
2. The Reviewer validates the response
3. Return a comprehensive, data-backed analysis

### 📊 Trading Mode

Click the **📊 Trading** button in the header to switch to the Trading Panel:

1. **Pattern Scanner** — Enter a ticker (e.g., `AAPL`) and click **🔍 Scan Patterns**
   - The system fetches 3 months of OHLCV data
   - Generates a candlestick chart image
   - Runs YOLOv8 AI inference (~10 seconds)
   - Shows detected patterns with confidence bars
   - Displays BUY/SELL/HOLD signal with reasoning

2. **Positions Tab** — View all open positions from your Alpaca account

3. **Orders Tab** — View recent trade history

---

## 🔍 YOLOv8 Pattern Detection

The system uses the [foduucom/stockmarket-pattern-detection-yolov8](https://huggingface.co/foduucom/stockmarket-pattern-detection-yolov8) model to detect 6 chart pattern types:

| Pattern | Type | Trading Signal |
|---------|------|----------------|
| Head and Shoulders Bottom | Bullish reversal | 🟢 BUY |
| W_Bottom (Double Bottom) | Bullish reversal | 🟢 BUY |
| Head and Shoulders Top | Bearish reversal | 🔴 SELL |
| M_Head (Double Top) | Bearish reversal | 🔴 SELL |
| Triangle | Continuation | 🟡 HOLD |
| StockLine | Trend line | 🟡 HOLD |

**How it works internally:**
1. `yfinance` fetches 3 months of daily OHLCV data
2. `mplfinance` generates a candlestick chart image
3. `ultralytics` YOLOv8 runs inference on the chart image
4. `signal_engine.py` converts patterns to a weighted BUY/SELL/HOLD signal

---

## 💰 Alpaca Broker Integration

The system integrates with [Alpaca Markets](https://alpaca.markets) for trade execution.

### Safety Guards
- **Paper trading by default** — No real money at risk
- **Max 100 shares per order** — Prevents accidental large trades
- **Max $10,000 per order** — Additional dollar-value safety limit
- **Agent shows signal first** — Always explains reasoning before trading
- **All trades logged** — Full audit trail

### Supported Operations
- ✅ Market orders (buy/sell)
- ✅ Limit orders
- ✅ Position tracking
- ✅ Account balance/buying power
- ✅ Close entire positions
- ✅ Order history

---

## 🛠️ API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/analyze` | Send query to the AI agent |
| `GET` | `/threads` | List all conversation threads |
| `GET` | `/threads/{id}` | Get conversation history |
| `DELETE` | `/threads/{id}` | Delete a conversation |
| `POST` | `/agent/stock` | Get dashboard data for a stock |
| `GET` | `/trading/account` | Alpaca account info |
| `GET` | `/trading/positions` | Open positions |
| `POST` | `/trading/scan/{symbol}` | Run YOLOv8 pattern scan |
| `GET` | `/trading/orders` | Recent order history |

---

## 🧰 Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React, Vite, Lucide Icons, ReactMarkdown |
| **Backend** | FastAPI, Uvicorn, Python |
| **AI/LLM** | LangGraph, LangChain, Groq (Llama 3.3), Google Gemini |
| **Pattern Detection** | YOLOv8 (ultralytics), mplfinance, yfinance |
| **Broker** | Alpaca Markets API (alpaca-py) |
| **Database** | PostgreSQL (Supabase) |
| **Data APIs** | Finnhub, AlphaVantage, DuckDuckGo |

---

## ⚠️ Disclaimer

> **This project is for educational and experimental purposes only.**
> It is NOT financial advice. Automated trading carries significant risk of financial loss.
> The YOLOv8 model has ~61% mAP accuracy — it should NOT be the sole basis for trading decisions.
> Always use paper trading first. Never risk money you can't afford to lose.

---

## 📝 License

MIT License — see [LICENSE](LICENSE) for details.
