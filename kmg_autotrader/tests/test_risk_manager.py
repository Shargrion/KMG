"""Tests for RiskManager with exposure, drawdown and daily loss limits."""

import pytest

from src.risk.risk_manager import RiskManager, RiskParameters


@pytest.mark.parametrize(
    "size,exposure,drawdown,daily_loss,expected",
    [
        (0.1, 0.1, 0.0, 0.0, True),
        (0.6, 0.0, 0.0, 0.0, False),  # trade size too big
        (0.3, 0.3, 0.0, 0.0, False),  # exposure exceeded
        (0.1, 0.1, 6.0, 0.0, False),  # drawdown breach
        (0.1, 0.1, 0.0, 6.0, False),  # daily loss breach
    ],
)
def test_validate(
    size: float, exposure: float, drawdown: float, daily_loss: float, expected: bool
) -> None:
    params = RiskParameters(
        max_position_percent=0.5, max_drawdown=5.0, max_daily_loss=5.0
    )
    manager = RiskManager(params)
    manager._current_drawdown = drawdown
    manager._daily_loss = daily_loss
    assert manager.validate(size, exposure) is expected


def test_update_pnl() -> None:
    params = RiskParameters(
        max_position_percent=0.5, max_drawdown=10.0, max_daily_loss=5.0
    )
    manager = RiskManager(params)

    manager.update_pnl(-2.0)
    assert manager._current_drawdown == pytest.approx(2.0)
    assert manager._daily_loss == pytest.approx(2.0)

    manager.update_pnl(1.0)
    assert manager._current_drawdown == pytest.approx(1.0)
    assert manager._daily_loss == pytest.approx(2.0)

    manager.update_pnl(2.0)
    assert manager._current_drawdown == pytest.approx(0.0)

