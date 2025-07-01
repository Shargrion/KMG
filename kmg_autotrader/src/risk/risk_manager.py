"""Risk management for trading operations."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import pickle

from src.webui.alerts.telegram_bot import send_alert
from src.analysis import performance_analyzer


@dataclass
class RiskParameters:
    max_position_percent: float
    max_drawdown: float
    min_confidence: float = 0.5
    risk_mode: str = "normal"  # "normal" or "conservative"


ML_MODEL_PATH = (
    Path(__file__).resolve().parents[2]
    / "project_metadata"
    / "MLModels"
    / "model_v1.pkl"
)


class RiskManager:
    """Validate trading signals against risk parameters."""

    def __init__(self, params: RiskParameters) -> None:
        """Initialize with risk parameters."""
        self._params = params
        self._current_drawdown = 0.0
        self._volume_factor = 1.0
        self._default_confidence = params.min_confidence

    # ------------------------------------------------------------------
    def auto_adjust(self, trades: int, threshold: float) -> None:
        """Automatically switch risk mode based on recent drawdown."""

        recent = performance_analyzer.get_recent_trades(trades)
        equity = performance_analyzer.pnl_equity(recent)
        dd = performance_analyzer.max_drawdown(equity)
        self._current_drawdown = dd
        if dd > threshold:
            self._set_conservative()
        else:
            self._set_normal()

    # ------------------------------------------------------------------
    def _set_conservative(self) -> None:
        if self._params.risk_mode == "conservative":
            return
        logging.warning("Switching to conservative risk mode")
        self._params.risk_mode = "conservative"
        self._volume_factor = 0.5
        self._params.min_confidence = max(0.9, self._params.min_confidence)

    def _set_normal(self) -> None:
        if self._params.risk_mode == "normal":
            return
        logging.info("Switching to normal risk mode")
        self._params.risk_mode = "normal"
        self._volume_factor = 1.0
        self._params.min_confidence = self._default_confidence

    # ------------------------------------------------------------------
    def scale_size(self, size: float) -> float:
        """Return trade size adjusted by current risk mode."""

        return size * self._volume_factor

    def validate(
        self,
        size: float,
        ask_model: bool = False,
        features: list[float] | None = None,
    ) -> bool:
        """Check if trade size is within limits and optionally consult ML."""
        size *= self._volume_factor
        if size > self._params.max_position_percent:
            logging.warning("Trade size %.2f exceeds limit", size)
            send_alert(
                f"Risk limit hit: size {size:.2f} > {self._params.max_position_percent:.2f}"
            )
            return False
        if self._current_drawdown > self._params.max_drawdown:
            logging.error("Drawdown limit reached")
            send_alert("Risk alert: drawdown limit reached")
            return False
        if ask_model:
            if features is None:
                logging.error("Model requested but no features supplied")
                send_alert("Risk check failed: no features for model")
                return False
            try:
                with ML_MODEL_PATH.open("rb") as f:
                    model = pickle.load(f)
                pred = int(model.predict([features])[0])
                logging.info("ML model decision: %d", pred)
                return bool(pred)
            except Exception as exc:  # noqa: BLE001
                logging.error("Model inference failed: %s", exc)
                send_alert(f"Risk model error: {exc}")
                return False

        logging.debug("Risk validation passed for size %.2f", size)
        return True
