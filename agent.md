# Agent: KMG-Autotrader

## 🧠 Purpose

Build a fully autonomous cryptocurrency trading bot with:
- Real-time + historical data collection from Binance
- Rule-based technical signal detection (SMA, RSI, ATR, etc.)
- GPT-assisted strategic decision making (chain-of-thought prompts)
- Strict validation and risk management of all actions
- Trade execution via Binance API
- Local storage of trades, signals, GPT logs, metrics
- Web-based UI for monitoring, configuration and analytics
- Daily ML training to improve model confidence
- Alerting via Telegram for critical states or rejections
- Full deployment automation via `install.sh`

---

## ⚙️ Key Features

- Binance REST + WebSocket collector with fallback
- Technical signal engine: crossover, RSI extremes, volatility triggers
- GPT logic with JSON-schema validation and rejection fallback
- Risk Manager layer: max position %, cooldown, drawdown control
- Secure, retryable Binance execution with logging
- PostgreSQL-backed local database
- Performance Analyzer: PnL, drawdown, Sharpe, win/loss ratio
- ML trainer using XGBoost or LightGBM
- Full-featured Web Dashboard with FastAPI/Flask backend and Chart.js frontend
- Telegram bot alerts for orders, risk breaches, GPT failures
- Fully typed, logged, commented Python codebase

---

## 💡 How It Works

1. **System starts** via `main.py`, loads config, starts scheduler.
2. **Collector** loads 1 year of history from Binance (REST) and starts WebSocket streaming.
3. **Rule Evaluator** receives data and checks for market triggers (e.g. SMA crosses, RSI levels).
4. **Trigger Module** invokes GPT if allowed and needed.
5. **GPT Controller** builds prompts from history + context and parses structured response.
6. **Risk Manager** validates signal ranges, exposure and constraints.
7. **Executor** places trades via Binance and logs all orders.
8. **Performance Analyzer** updates metrics and provides analytics.
9. **ML Trainer** runs daily on signals + outcomes to evolve local model.
10. **Web UI** offers metrics, controls, logs, risk editor and GPT feedback.
11. **Alerts** are pushed to Telegram on failures, rejections, limit hits.

---

## 📁 Directory Structure

```
kmg_autotrader/
├── main.py                        # Entry orchestrator
├── install.sh                     # One-command setup script
├── requirements.txt
├── .env.example                   # Env template with API keys and DB info
├── project_metadata/
│   ├── schema/gpt_response_schema.json
│   ├── gpt_log_archive.db
│   └── MLModels/model_v1.pkl
├── src/
│   ├── collector/binance_data_collector.py
│   ├── evaluator/rule_evaluator.py
│   ├── trigger/gpt_trigger.py
│   ├── trigger/gpt_controller.py
│   ├── risk/risk_manager.py
│   ├── executor/executor.py
│   ├── analysis/performance_analyzer.py
│   ├── analysis/ml_trainer.py
│   └── webui/
│       ├── backend.py                  # REST API, template renderer
│       ├── templates/                  # Jinja2: dashboard.html, logs.html
│       ├── static/
│       │   ├── css/, js/, img/
│       └── alerts/telegram_bot.py      # Telegram alert logic
├── tests/                              # Unit + integration tests
```

---

## 🌐 Web Interface

### Backend (`webui/backend.py`)
- Built with **FastAPI** or **Flask**
- Serves:
  - `/metrics` → returns JSON of live stats
  - `/signals` → current & rejected signals
  - `/risk` (GET/PUT) → risk parameters
  - `/logs` → logs from GPT, trades
  - `/ml/status` → last model + accuracy
  - Static UI from `/templates` + `/static`

### Frontend (`templates/ + static/`)
- Jinja2 templates or HTML + Chart.js:
  - Live equity curve
  - Open/closed trades
  - Rule/GPT signal flow
  - Rejection reasons
  - GPT confidence history

### Alerts (`telegram_bot.py`)
- Requires TELEGRAM_TOKEN, CHAT_ID in `.env`
- Sends:
  - GPT errors or invalid signals
  - Trade errors
  - Risk limit breaches
  - Daily PnL summary (optional)

---

## ⚙️ install.sh Requirements

The `install.sh` must:
- Install system packages:
  - `python3`, `python3-venv`, `python3-pip`
  - `postgresql`, `git`, `build-essential`
- Create PostgreSQL user & DB:
  - `kmg_user` / `kmg_autotrader`
- Setup virtualenv + pip install
- Echo next steps:
  - Copy `.env.example` to `.env`
  - Configure OpenAI, Binance, DB credentials
  - Run `python main.py`

---

## 🔐 .env Variables Required

```
OPENAI_API_KEY=
BINANCE_API_KEY=
BINANCE_SECRET_KEY=
POSTGRES_URL=postgresql://kmg_user:password@localhost/kmg_autotrader
TELEGRAM_TOKEN=
TELEGRAM_CHAT_ID=
MAX_POSITION_PERCENT=0.2
MAX_DRAWDOWN=5.0
GPT_CALL_LIMIT_PER_HOUR=10
```

---

## 🛠 Dev Standards

- Python 3.11+
- PEP8 + black formatting
- Type hints (PEP 484)
- Logging in every module
- All classes/methods documented with docstrings
- GPT responses validated with JSON Schema (`pydantic` or `jsonschema`)
- Retry handling on API calls
- Graceful degradation if GPT or Binance fails

---

## ✅ How to Start

1. Run: `bash install.sh`
2. Configure `.env` with your keys and DB string
3. Run the bot: `python main.py`
4. Open web dashboard on `http://localhost:8000` (or Flask port)
5. Monitor trades, configure risk, review logs
6. Set up screen or systemd to daemonize

---

This file serves as the full spec for Codex or SWE-agent.
It includes project structure, module responsibilities, UI, risk model, and boot instructions.