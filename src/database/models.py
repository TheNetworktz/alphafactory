"""
AlphaFactory OS - Database Models
SQLAlchemy ORM models for storing market data, trades, and performance
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, 
    Text, Index, ForeignKey, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Symbol(Base):
    """
    Stock symbols and metadata
    """
    __tablename__ = 'symbols'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(255))
    exchange = Column(String(50))
    sector = Column(String(100))
    industry = Column(String(100))
    market_cap = Column(Float)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    daily_bars = relationship('DailyBar', back_populates='symbol', cascade='all, delete-orphan')
    trades = relationship('Trade', back_populates='symbol', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<Symbol(symbol='{self.symbol}', name='{self.name}')>"


class DailyBar(Base):
    """
    Daily OHLCV (Open, High, Low, Close, Volume) data
    """
    __tablename__ = 'daily_bars'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol_id = Column(Integer, ForeignKey('symbols.id'), nullable=False)
    date = Column(DateTime, nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    adj_close = Column(Float)  # Adjusted close for splits/dividends
    
    # Technical indicators (pre-calculated for performance)
    sma_20 = Column(Float)
    sma_50 = Column(Float)
    sma_200 = Column(Float)
    rsi_14 = Column(Float)
    macd = Column(Float)
    macd_signal = Column(Float)
    bbands_upper = Column(Float)
    bbands_middle = Column(Float)
    bbands_lower = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    symbol = relationship('Symbol', back_populates='daily_bars')
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('symbol_id', 'date', name='uq_symbol_date'),
        Index('idx_symbol_date', 'symbol_id', 'date'),
    )
    
    def __repr__(self):
        return f"<DailyBar(symbol_id={self.symbol_id}, date='{self.date}', close={self.close})>"


class Strategy(Base):
    """
    Trading strategies and their configurations
    """
    __tablename__ = 'strategies'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text)
    version = Column(String(20))
    parameters = Column(Text)  # JSON string of parameters
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    backtests = relationship('Backtest', back_populates='strategy', cascade='all, delete-orphan')
    trades = relationship('Trade', back_populates='strategy', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<Strategy(name='{self.name}', version='{self.version}')>"


class Backtest(Base):
    """
    Backtest runs and results
    """
    __tablename__ = 'backtests'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(Integer, ForeignKey('strategies.id'), nullable=False)
    name = Column(String(255))
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    initial_capital = Column(Float, nullable=False)
    
    # Performance metrics
    final_equity = Column(Float)
    total_return = Column(Float)
    annual_return = Column(Float)
    sharpe_ratio = Column(Float)
    sortino_ratio = Column(Float)
    max_drawdown = Column(Float)
    win_rate = Column(Float)
    profit_factor = Column(Float)
    total_trades = Column(Integer)
    winning_trades = Column(Integer)
    losing_trades = Column(Integer)
    
    # Execution details
    commission_total = Column(Float)
    slippage_total = Column(Float)
    
    # Status
    status = Column(String(20), default='pending')  # pending/running/completed/failed
    error_message = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # Relationships
    strategy = relationship('Strategy', back_populates='backtests')
    trades = relationship('Trade', back_populates='backtest', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<Backtest(id={self.id}, strategy_id={self.strategy_id}, total_return={self.total_return})>"


class Trade(Base):
    """
    Individual trades (both backtest and live)
    """
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(Integer, ForeignKey('strategies.id'), nullable=False)
    backtest_id = Column(Integer, ForeignKey('backtests.id'), nullable=True)  # NULL for live trades
    symbol_id = Column(Integer, ForeignKey('symbols.id'), nullable=False)
    
    # Trade details
    trade_type = Column(String(10), nullable=False)  # LONG/SHORT
    entry_date = Column(DateTime, nullable=False, index=True)
    entry_price = Column(Float, nullable=False)
    entry_quantity = Column(Float, nullable=False)
    
    exit_date = Column(DateTime, index=True)
    exit_price = Column(Float)
    exit_quantity = Column(Float)
    exit_reason = Column(String(50))  # stop_loss/take_profit/signal/manual
    
    # P&L
    gross_pnl = Column(Float)
    commission = Column(Float)
    slippage = Column(Float)
    net_pnl = Column(Float)
    return_pct = Column(Float)
    
    # Trade metadata
    signal_strength = Column(Float)  # 0-1 confidence
    notes = Column(Text)
    is_live = Column(Boolean, default=False)  # Live vs backtest
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    strategy = relationship('Strategy', back_populates='trades')
    backtest = relationship('Backtest', back_populates='trades')
    symbol = relationship('Symbol', back_populates='trades')
    
    # Indexes for query performance
    __table_args__ = (
        Index('idx_trade_dates', 'entry_date', 'exit_date'),
        Index('idx_trade_symbol', 'symbol_id', 'entry_date'),
    )
    
    def __repr__(self):
        return f"<Trade(id={self.id}, symbol_id={self.symbol_id}, net_pnl={self.net_pnl})>"


class PerformanceSnapshot(Base):
    """
    Daily portfolio performance snapshots
    """
    __tablename__ = 'performance_snapshots'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False, index=True)
    strategy_id = Column(Integer, ForeignKey('strategies.id'), nullable=True)
    backtest_id = Column(Integer, ForeignKey('backtests.id'), nullable=True)
    
    # Portfolio values
    equity = Column(Float, nullable=False)
    cash = Column(Float, nullable=False)
    positions_value = Column(Float, nullable=False)
    
    # Performance metrics
    daily_return = Column(Float)
    cumulative_return = Column(Float)
    drawdown = Column(Float)
    
    # Risk metrics
    volatility = Column(Float)
    sharpe_ratio = Column(Float)
    beta = Column(Float)  # vs benchmark
    
    # Position details
    num_positions = Column(Integer)
    largest_position_pct = Column(Float)
    
    is_live = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_perf_date', 'date'),
        Index('idx_perf_strategy', 'strategy_id', 'date'),
    )
    
    def __repr__(self):
        return f"<PerformanceSnapshot(date='{self.date}', equity={self.equity})>"


class EarningsCalendar(Base):
    """
    Earnings announcement dates (to avoid trading around earnings)
    """
    __tablename__ = 'earnings_calendar'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol_id = Column(Integer, ForeignKey('symbols.id'), nullable=False)
    earnings_date = Column(DateTime, nullable=False, index=True)
    fiscal_quarter = Column(String(10))
    estimate_eps = Column(Float)
    actual_eps = Column(Float)
    surprise_pct = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_earnings_symbol_date', 'symbol_id', 'earnings_date'),
    )
    
    def __repr__(self):
        return f"<EarningsCalendar(symbol_id={self.symbol_id}, date='{self.earnings_date}')>"