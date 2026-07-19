
# 📊 QuantPilot — AI Stock Analyzer & Trading Agent

An AI-powered multi-agent platform for stock research, chart-pattern detection, and optional automated trading. Designed for experimentation and development — not financial advice.

## Table of contents
- Quick Start
- Features
- Architecture
- Project layout
- Prerequisites & configuration
- Run (backend & frontend)
- Usage
- Development & testing
- Contributing
- License

## Quick Start

1. Create a Python virtual environment and install dependencies:

```bash
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # macOS / Linux
pip install -r requirements.txt
```

2. Add required API keys to a `.env` file in the project root (see `Prerequisites & configuration`).

3. Start the backend and frontend in separate terminals:

```bash
# Backend
uvicorn backend.app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 in your browser.

## Features

- Natural-language AI analyst + reviewer agents (tool-enabled)
- YOLOv8 chart-pattern detection (candlestick images)
- Pattern → BUY/SELL/HOLD signal engine
- Optional Alpaca integration for paper trading
- React + Vite frontend with Chat and Trading panels

## Architecture (high level)

Frontend (React/Vite) ↔ FastAPI backend ↔ Tools (data, detection, broker) ↔ PostgreSQL

Key components:
- `backend/agents/stock_agent.py` — multi-agent orchestration
- `backend/pattern_detection/pattern_detector.py` — image generation + YOLOv8 inference
- `backend/trading/signal_engine.py` — converts detected patterns into signals
- `frontend/src` — React app (Chat + Trading UI)

## Project layout

See the project tree for main modules and where to look for features.

## Prerequisites & configuration

- Python 3.10+
- Node.js 18+
- Git

Create a `.env` file with the following (only include keys you use):

```env
GROQ_API_KEY=
GOOGLE_API_KEY=
HUGGINGFACEHUB_API_TOKEN=
DATABASE_URL=postgresql://user:pass@host:5432/dbname
FINNHUB_API_KEY=
ALPHAADVANTAGE_API_KEY=
ALPACA_API_KEY=
ALPACA_SECRET_KEY=
ALPACA_PAPER=true
```

Notes:
- Alpaca is optional — without it you cannot execute trades but analysis and scanning still work.
- Keep sensitive keys out of version control.

## Run

Backend (from project root):

```bash
uvicorn backend.app.main:app --reload --port 8000
```

Frontend (in a new terminal):

```bash
cd frontend
npm install
npm run dev
```

API server default: http://127.0.0.1:8000
Frontend default: http://localhost:5173

## Usage

- Chat: ask natural-language stock questions (price, fundamentals, comparisons, pattern scans).
- Trading panel: scan a ticker for patterns, review signals, optionally place paper trades via Alpaca.

Recommended flow:
1. Scan patterns for a ticker.
2. Review detected patterns and the generated signal reasoning.
3. Use paper trading only until you validate behavior.

## Development & testing

- Run linting and format with your preferred tools (pre-commit not included by default).
- Unit tests: add tests under `tests/` and run with `pytest`.

## Contributing

If you'd like to contribute:

1. Fork the repository and create a feature branch.
2. Add tests for new behavior and update documentation as needed.
3. Open a PR describing the change and rationale.

## Contact

For questions or issues, open an issue in the repository.

## Disclaimer

This project is experimental and educational. It is NOT financial advice. Use paper trading and do not risk funds you cannot afford to lose.

## License

MIT — see [LICENSE](LICENSE) for details.
