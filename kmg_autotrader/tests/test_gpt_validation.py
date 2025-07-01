"""GPT response validation tests."""

from src.trigger.gpt_controller import GPTController


def test_parse_invalid(monkeypatch):
    controller = GPTController(api_key="test")

    def dummy(*args, **kwargs):
        raise ValueError("fail")

    monkeypatch.setattr(controller, "send_prompt", dummy)
    assert controller.send_prompt("hi") is None
