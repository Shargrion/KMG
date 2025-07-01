import builtins
from unittest import mock

import pytest

from src.webui.alerts import telegram_bot


def test_send_alert(monkeypatch):
    calls = {}

    def fake_post(url, data=None, timeout=None):
        calls['url'] = url
        calls['data'] = data
        return mock.Mock(status_code=200)

    monkeypatch.setenv('TELEGRAM_TOKEN', 'token')
    monkeypatch.setenv('TELEGRAM_CHAT_ID', '123')
    monkeypatch.setattr(telegram_bot, 'requests', mock.Mock(post=fake_post))
    telegram_bot._BOT = None

    telegram_bot.send_alert('hello')

    assert 'bottoken' in calls['url']
    assert calls['data']['chat_id'] == '123'
    assert calls['data']['text'] == 'hello'


def test_rate_limit(monkeypatch):
    send_count = 0

    def fake_post(url, data=None, timeout=None):
        nonlocal send_count
        send_count += 1
        return mock.Mock(status_code=200)

    monkeypatch.setenv('TELEGRAM_TOKEN', 'token')
    monkeypatch.setenv('TELEGRAM_CHAT_ID', '123')
    monkeypatch.setattr(telegram_bot, 'requests', mock.Mock(post=fake_post))
    telegram_bot._BOT = None

    telegram_bot.send_alert('one')
    telegram_bot.send_alert('two')

    assert send_count == 1
