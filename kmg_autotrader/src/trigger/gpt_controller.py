"""Interact with OpenAI GPT models."""

import json
import logging
from pathlib import Path

import openai
from pydantic import BaseModel, ValidationError

from src.webui.alerts.telegram_bot import send_alert

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "project_metadata" / "schema" / "gpt_response_schema.json"


class GPTResponse(BaseModel):
    direction: str
    size: float
    stop_loss: float
    take_profit: float
    confidence: float


class GPTController:
    """Handle GPT prompt construction and response validation."""

    def __init__(self, api_key: str) -> None:
        """Initialize controller with the given OpenAI API key."""
        openai.api_key = api_key

    def send_prompt(self, prompt: str) -> GPTResponse | None:
        """Send a prompt to OpenAI and validate the structured response."""
        try:
            logging.info("Sending prompt to OpenAI")
            completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}]
            )
            data = completion.choices[0].message.content
            logging.debug("GPT raw response: %s", data)
            parsed = json.loads(data)
            response = GPTResponse(**parsed)
            logging.info("GPT response validated with confidence %.2f", response.confidence)
            return response
        except (openai.error.OpenAIError, json.JSONDecodeError, ValidationError) as exc:
            logging.error("GPT error: %s", exc)
            send_alert(f"GPT error: {exc}")
            return None
