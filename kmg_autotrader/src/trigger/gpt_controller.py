"""Interact with OpenAI GPT models."""

import json
import logging
import os
import sqlite3
import time
from pathlib import Path
from typing import Iterable

import openai
from pydantic import BaseModel, ValidationError

from src.collector.binance_data_collector import Candle
from src.evaluator.rule_evaluator import evaluate_rules
from src.risk.risk_manager import RiskParameters
from src.webui.alerts.telegram_bot import send_alert

BASE_PATH = Path(__file__).resolve().parents[2] / "project_metadata"
SCHEMA_PATH = BASE_PATH / "schema" / "gpt_response_schema.json"
DB_PATH = BASE_PATH / "gpt_log_archive.db"


class GPTResponse(BaseModel):
    direction: str
    size: float
    stop_loss: float
    take_profit: float
    confidence: float


class GPTController:
    """Handle GPT prompt construction and response validation."""

    def __init__(self, api_key: str) -> None:
        """Initialize controller with the given OpenAI API key and database."""

        openai.api_key = api_key
        self._init_db()
        with SCHEMA_PATH.open("r") as f:
            self._schema = json.load(f)
        self._last_error: str | None = None

    # ------------------------------------------------------------------
    def _validate_schema(self, data: dict) -> None:
        """Validate response dict against loaded JSON schema."""

        for key in self._schema.get("required", []):
            if key not in data:
                raise ValueError(f"Missing required field: {key}")
        for key, prop in self._schema.get("properties", {}).items():
            if key not in data:
                continue
            t = prop.get("type")
            if t == "number" and not isinstance(data[key], (int, float)):
                raise ValueError(f"Field {key} must be a number")
            if t == "string" and not isinstance(data[key], str):
                raise ValueError(f"Field {key} must be a string")

    def _init_db(self) -> None:
        """Create the log table if necessary."""

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS gpt_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    prompt TEXT,
                    response TEXT,
                    success INTEGER
                )
                """
            )

    def build_prompt(
        self,
        candles: Iterable[Candle],
        position: float,
        risk: RiskParameters,
    ) -> str:
        """Construct a textual prompt for GPT from recent candles and risk."""

        prices = ",".join(f"{c.close:.2f}" for c in candles)
        prompt = (
            "Market closes: "
            f"[{prices}]\nCurrent position: {position}\n"
            f"Max position: {risk.max_position_percent}\n"
            f"Max drawdown: {risk.max_drawdown}\n"
            "Return JSON with direction, size, stop_loss, take_profit, confidence"
        )
        return prompt

    def send_prompt(self, prompt: str) -> GPTResponse | None:
        """Send a prompt to OpenAI and validate the structured response."""

        start = time.perf_counter()
        raw_response: str | None = None
        success = 0
        try:
            logging.info("Sending prompt to OpenAI")
            completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
            )
            raw_response = completion.choices[0].message.content
            logging.debug("GPT raw response: %s", raw_response)
            parsed = json.loads(raw_response)
            self._validate_schema(parsed)
            response = GPTResponse(**parsed)
            logging.info(
                "GPT response validated with confidence %.2f in %.2fs",
                response.confidence,
                time.perf_counter() - start,
            )
            success = 1
            self._last_error = None
            return response
        except (
            openai.error.OpenAIError,
            json.JSONDecodeError,
            ValidationError,
            ValueError,
        ) as exc:
            logging.error("GPT error: %s", exc)
            self._last_error = str(exc)
            raw_response = raw_response or str(exc)
            send_alert(f"GPT error: {exc}")
            return None
        finally:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    "INSERT INTO gpt_logs(prompt, response, success) VALUES (?, ?, ?)",
                    (prompt, raw_response, success),
                )

    def request_decision(
        self,
        candles: Iterable[Candle],
        position: float,
        risk: RiskParameters,
    ) -> GPTResponse | None:
        """Build prompt from context, send to GPT and return parsed response."""

        prompt = self.build_prompt(candles, position, risk)
        response = self.send_prompt(prompt)
        if response is None:
            logging.warning(
                "Falling back to rule evaluator due to GPT failure: %s",
                self._last_error,
            )
            evaluate_rules([c.close for c in candles])
            return None
        return response

