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

from src.analysis.performance_analyzer import Trade, compute_metrics
from src.evaluator.rule_evaluator import Signal
from src.risk.risk_manager import RiskParameters

logger = logging.getLogger(__name__)


BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI()


# ---------------------------------------------------------------------------
# In-memory stores. In a real implementation these would be backed by a
# database. They are kept extremely simple here for demonstration purposes.
# ---------------------------------------------------------------------------
TRADES: list[Trade] = []
ACTIVE_SIGNALS: list[Signal] = []
REJECTED_SIGNALS: list[tuple[Signal, str]] = []
RISK_PARAMS = RiskParameters(max_position_percent=0.1, max_drawdown=5.0)
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
    """Return PnL statistics and equity curve."""

    logger.info("/metrics requested")
    return _gather_metrics()


@app.get("/signals")
def signals() -> dict[str, Any]:
    """Return active and rejected trading signals."""

    logger.info("/signals requested")
    return {
        "active": [asdict(sig) for sig in ACTIVE_SIGNALS],
        "rejected": [
            {"signal": asdict(sig), "reason": reason}
            for sig, reason in REJECTED_SIGNALS
        ],
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


@app.put("/risk")
def update_risk(params: RiskModel = Body(...)) -> dict[str, float]:
    """Update risk management parameters."""

    logger.info("/risk PUT requested: %s", params)
    RISK_PARAMS.max_position_percent = params.max_position_percent
    RISK_PARAMS.max_drawdown = params.max_drawdown
    return asdict(RISK_PARAMS)


@app.get("/logs")
def logs(limit: int = 20) -> dict[str, list[str]]:
    """Return last GPT actions and trade logs."""

    logger.info("/logs requested, limit=%d", limit)
    return {"entries": LOGS[-limit:]}

