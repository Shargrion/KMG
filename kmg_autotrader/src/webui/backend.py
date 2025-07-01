"""Web backend using FastAPI.

This module exposes a minimal REST API used by the web dashboard. The actual
trading logic is out of scope for this file; instead we provide lightweight
in-memory stores that tests can interact with.  The endpoints are intentionally
simple and return JSON structures so the front-end can poll them easily.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.analysis.performance_analyzer import Trade, compute_metrics
from src.risk.risk_manager import RiskParameters


BASE_PATH = Path(__file__).resolve().parent

app = FastAPI()

# Jinja2 templates and static file mounting -------------------------------
templates = Jinja2Templates(directory=str(BASE_PATH / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_PATH / "static")), name="static")


# In-memory stores used for demonstration and unit tests -----------------
TRADES: List[Trade] = []
SIGNALS: List[Dict[str, Any]] = []
REJECTIONS: List[str] = []
RISK = RiskParameters(max_position_percent=0.5, max_drawdown=10.0)
LOGS: List[str] = []


@app.get("/")
async def dashboard(request: Request) -> Any:
    """Render the dashboard template."""
    equity = [t.pnl for t in TRADES]
    context = {
        "request": request,
        "trades": TRADES,
        "rejections": REJECTIONS,
        "equity": equity,
    }
    return templates.TemplateResponse("dashboard.html", context)


@app.get("/metrics")
def metrics() -> Dict[str, Any]:
    """Return basic performance metrics."""
    return compute_metrics(TRADES)


@app.get("/signals")
def get_signals() -> Dict[str, Any]:
    """Return latest signals and rejection reasons."""
    return {"signals": SIGNALS, "rejections": REJECTIONS}


@app.get("/risk")
def get_risk() -> Dict[str, float]:
    """Return current risk parameters."""
    return {
        "max_position_percent": RISK.max_position_percent,
        "max_drawdown": RISK.max_drawdown,
    }


@app.put("/risk")
async def update_risk(params: RiskParameters) -> Dict[str, float]:
    """Update risk parameters."""
    RISK.max_position_percent = params.max_position_percent
    RISK.max_drawdown = params.max_drawdown
    return {
        "max_position_percent": RISK.max_position_percent,
        "max_drawdown": RISK.max_drawdown,
    }


@app.get("/logs")
def get_logs() -> Dict[str, List[str]]:
    """Return recent log entries."""
    return {"logs": LOGS}

