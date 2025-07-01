"""Interact with OpenAI GPT models."""

import json
import logging
from pathlib import Path
from typing import Any, Dict
from dataclasses import dataclass

try:
    import openai
except ImportError:  # pragma: no cover - optional dependency
    openai = None

try:
    from pydantic import BaseModel, ValidationError
except ImportError:  # pragma: no cover - optional dependency
    BaseModel = None  # type: ignore
    ValidationError = Exception

SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "project_metadata"
    / "schema"
    / "gpt_response_schema.json"
)


if BaseModel:
    class GPTResponse(BaseModel):
        direction: str
        size: float
        stop_loss: float
        take_profit: float
        confidence: float

else:
    @dataclass
    class GPTResponse:  # pragma: no cover - used only without pydantic
        direction: str
        size: float
        stop_loss: float
        take_profit: float
        confidence: float


class GPTController:
    """Handle GPT prompt construction and response validation."""

    def __init__(self, api_key: str) -> None:
        if openai:
            openai.api_key = api_key

    def send_prompt(self, prompt: str) -> GPTResponse | None:
        if not openai:
            logging.error("openai package not available")
            return None
        try:
            logging.info("Sending prompt to OpenAI")
            completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}]
            )
            data = completion.choices[0].message.content
            logging.debug("GPT raw response: %s", data)
            parsed = json.loads(data)
            return GPTResponse(**parsed)
        except (openai.error.OpenAIError, json.JSONDecodeError, ValidationError) as exc:
            logging.error("GPT error: %s", exc)
            return None
