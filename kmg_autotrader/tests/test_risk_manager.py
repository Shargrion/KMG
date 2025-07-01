"""Tests for RiskManager."""

from src.risk.risk_manager import RiskManager, RiskParameters
from src.analysis import performance_analyzer


def test_validate():
    params = RiskParameters(max_position_percent=0.5, max_drawdown=10)
    manager = RiskManager(params)
    assert manager.validate(0.4)
    assert not manager.validate(0.6)


def test_auto_adjust(monkeypatch):
    params = RiskParameters(
        max_position_percent=1.0,
        max_drawdown=10.0,
        min_confidence=0.5,
        risk_mode="normal",
    )
    manager = RiskManager(params)

    trades = [
        performance_analyzer.Trade(pnl=-0.6),
        performance_analyzer.Trade(pnl=-0.6),
    ]

    monkeypatch.setattr(performance_analyzer, "get_recent_trades", lambda n: trades)

    manager.auto_adjust(2, 0.5)

    assert manager._params.risk_mode == "conservative"
    assert manager._volume_factor == 0.5
    assert manager._params.min_confidence >= 0.9
