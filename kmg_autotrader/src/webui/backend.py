"""Web backend using FastAPI.

Endpoints expose metrics and recent trade signals from the PostgreSQL
database.  Errors are logged and returned as HTTP 500 responses.
"""

import logging
from fastapi import FastAPI, HTTPException

from src.analysis.performance_analyzer import compute_db_metrics
from src.db import SessionLocal
from src.db.models import TradeLog

app = FastAPI()


@app.get("/metrics")
def metrics() -> dict:
    """Return performance metrics computed from the database."""
    try:
        with SessionLocal() as session:
            return compute_db_metrics(session)
    except Exception as exc:  # pragma: no cover - just in case
        logging.error("Metrics endpoint failed: %s", exc)
        raise HTTPException(status_code=500, detail="metrics unavailable")


@app.get("/signals")
def signals(limit: int = 10) -> list[dict]:
    """Return the most recent trade signals."""
    try:
        with SessionLocal() as session:
            trades = (
                session.query(TradeLog)
                .order_by(TradeLog.timestamp.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "timestamp": t.timestamp.isoformat(),
                    "symbol": t.symbol,
                    "side": t.side,
                    "status": t.status.value,
                    "pnl": t.pnl,
                }
                for t in trades
            ]
    except Exception as exc:  # pragma: no cover - just in case
        logging.error("Signals endpoint failed: %s", exc)
        raise HTTPException(status_code=500, detail="signals unavailable")
