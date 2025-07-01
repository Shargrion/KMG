"""Tests for RiskManager."""

from src.risk.risk_manager import RiskManager, RiskParameters


def test_validate():
    params = RiskParameters(max_position_percent=0.5, max_drawdown=10)
    manager = RiskManager(params)
    assert manager.validate(0.4)
    assert not manager.validate(0.6)
