"""Database models used by the application."""

from datetime import datetime
from enum import Enum

from sqlalchemy import Column, DateTime, Enum as SqlEnum, Float, Integer, String

from . import Base


class TradeStatus(str, Enum):
    """Possible trade outcomes."""

    WIN = "WIN"
    LOSS = "LOSS"
    REJECTED = "REJECTED"


class TradeLog(Base):
    """Record of an executed or rejected trade."""

    __tablename__ = "trade_log"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    symbol = Column(String, nullable=False, index=True)
    side = Column(String, nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float)
    pnl = Column(Float)
    status = Column(SqlEnum(TradeStatus), default=TradeStatus.REJECTED, index=True)
