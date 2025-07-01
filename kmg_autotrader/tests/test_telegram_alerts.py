"""Tests for Telegram alerting."""

from src.webui.alerts import telegram_bot


def test_send_alert(monkeypatch):
    calls = {}

    def fake_post(url, data=None, timeout=None):
        calls["url"] = url
        calls["data"] = data
        return telegram_bot.requests.Response()

    monkeypatch.setattr(telegram_bot, "_bot", None)
    monkeypatch.setattr(telegram_bot.requests, "post", fake_post)
    monkeypatch.setenv("TELEGRAM_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat")
    monkeypatch.setattr(telegram_bot.time, "time", lambda: 10)

    telegram_bot.send_alert("hello")

    assert calls["data"]["text"] == "hello"

    calls.clear()
    telegram_bot.send_alert("again")
    # Because time is still 0, second call should be skipped
    assert calls == {}
