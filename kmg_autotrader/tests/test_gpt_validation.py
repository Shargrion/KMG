"""GPT response validation tests."""

from src.trigger import gpt_controller

GPTController = gpt_controller.GPTController


def test_parse_invalid(monkeypatch):
    controller = GPTController(api_key="test")

    def dummy(*args, **kwargs):
        raise gpt_controller.openai.error.OpenAIError("fail")

    monkeypatch.setattr(
        "src.trigger.gpt_controller.openai.ChatCompletion.create", dummy
    )
    assert controller.send_prompt("hi") is None
