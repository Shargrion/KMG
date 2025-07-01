"""FastAPI backend exposing bot metrics and logs."""

from __future__ import annotations

import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from src.analysis.performance_analyzer import (
    Trade,
    compute_metrics,
    compute_db_metrics,
    get_recent_trades,
)
from src.evaluator.rule_evaluator import Signal
from src.risk.risk_manager import RiskParameters

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI()


# ---------------------------------------------------------------------------
# In-memory stores used mainly for tests. Real usage relies on the database.
# ---------------------------------------------------------------------------
TRADES: list[Trade] = []
ACTIVE_SIGNALS: list[Signal] = []
REJECTED_SIGNALS: list[tuple[Signal, str]] = []
RISK_PARAMS = RiskParameters(
    max_position_percent=0.1,
    max_drawdown=5.0,
    min_confidence=0.5,
    risk_mode="normal",
)
LOGS: list[str] = []


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request) -> Any:
    """Render the main dashboard with equity curve and recent activity."""

    metrics = _gather_metrics()
    context = {
        "request": request,
        "equity_curve": metrics["equity_curve"],
        "trades": TRADES,
        "rejected_signals": [
            {"signal": asdict(sig), "reason": reason}
            for sig, reason in REJECTED_SIGNALS
        ],
    }
    logger.debug("Rendering dashboard with %d trades", len(TRADES))
    return templates.TemplateResponse("dashboard.html", context)


def _gather_metrics() -> dict[str, Any]:
    """Helper to compute metrics from stored trades."""

    metrics = compute_metrics(TRADES)
    equity: list[float] = []
    cumulative = 0.0
    for trade in TRADES:
        cumulative += trade.pnl
        equity.append(cumulative)
    metrics["equity_curve"] = equity
    logger.debug("Metrics computed: %s", metrics)
    return metrics


@app.get("/metrics")
def metrics() -> dict[str, Any]:
    """Return PnL statistics from the database."""

    logger.info("/metrics requested")
    return compute_db_metrics()


@app.get("/signals")
def signals(limit: int = 20) -> dict[str, Any]:
    """Return last N trading signals and their status."""

    logger.info("/signals requested limit=%d", limit)
    trades = get_recent_trades(limit)
    return {
        "signals": [
            {
                "timestamp": t.timestamp.isoformat(),
                "symbol": t.symbol,
                "side": t.side,
                "status": t.status,
            }
            for t in trades[::-1]
        ]
    }


@app.get("/risk")
def get_risk() -> dict[str, float]:
    """Return current risk management parameters."""

    logger.info("/risk GET requested")
    return asdict(RISK_PARAMS)


class RiskModel(BaseModel):
    """Pydantic model for editing risk parameters."""

    max_position_percent: float
    max_drawdown: float
    min_confidence: float
    risk_mode: str


@app.put("/risk")
def update_risk(params: RiskModel = Body(...)) -> dict[str, float]:
    """Update risk management parameters."""

    logger.info("/risk PUT requested: %s", params)
    RISK_PARAMS.max_position_percent = params.max_position_percent
    RISK_PARAMS.max_drawdown = params.max_drawdown
    RISK_PARAMS.min_confidence = params.min_confidence
    RISK_PARAMS.risk_mode = params.risk_mode
    return asdict(RISK_PARAMS)


@app.get("/logs")
def logs(limit: int = 20) -> dict[str, list[str]]:
    """Return last GPT actions and trade logs."""

    logger.info("/logs requested, limit=%d", limit)
    return {"entries": LOGS[-limit:]}
