"""
STM (Short-Term Mean Reversion) Strategy for AlphaFactory OS
Phase 1: Primary Profit Generator

Author: AlphaFactory OS
Strategy Type: Mean Reversion
Timeframe: 1-5 day holds
Target: >60% win rate, >2.0 profit factor

Entry Rules:
1. Price < Lower Bollinger Band (20, 2)
2. RSI(14) < 30 (oversold)
3. Volume > 1.5x average (capitulation)
4. Not within 5 days of earnings
5. Quality filters (price $10-500, volume >500K, mcap >$1B)

Exit Rules:
1. Price hits middle Bollinger Band (primary exit)
2. RSI > 50 (momentum reversal)
3. 5% stop-loss (risk management)
4. 5-day maximum hold (force exit)
5. 2% trailing stop (lock profits)

Position Sizing:
- ATR-based volatility sizing
- Risk 2% per trade
- Max 10% per position
- Max 10 concurrent positions
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta


class STM_MeanReversion:
    """
    Short-Term Mean Reversion Strategy
    
    Designed for quick 1-5 day profit generation.
    High win rate, controlled risk, fast feedback loop.
    """
    
    def __init__(
        self,
        # Strategy name
        name: str = "STM_MeanReversion",
        
        # Bollinger Bands
        bb_period: int = 20,
        bb_std_dev: float = 2.0,
        price_below_bb_threshold: float = 0.01,  # 1% below lower BB
        
        # RSI
        rsi_period: int = 14,
        rsi_oversold: float = 30.0,
        rsi_exit_threshold: float = 50.0,
        
        # Volume
        volume_period: int = 20,
        volume_surge_ratio: float = 1.5,
        
        # Stock Quality Filters
        min_price: float = 10.0,
        max_price: float = 500.0,
        min_avg_volume: int = 500000,
        min_market_cap: float = 1e9,  # $1 billion
        
        # Earnings Avoidance
        avoid_earnings: bool = True,
        days_before_earnings: int = 5,
        days_after_earnings: int = 2,
        
        # Exit Rules
        exit_at_bb_middle: bool = True,
        exit_at_rsi_threshold: bool = True,
        max_hold_days: int = 5,
        
        # Risk Management
        stop_loss_pct: float = 0.05,  # 5%
        trailing_stop_pct: float = 0.02,  # 2%
        use_trailing_stop: bool = True,
        
        # Position Sizing
        risk_per_trade_pct: float = 0.02,  # 2%
        max_position_pct: float = 0.10,  # 10%
        use_atr_sizing: bool = True,
        atr_period: int = 14,
        atr_multiplier: float = 2.5,
        
        # Portfolio
        max_concurrent_positions: int = 10,
        equal_weighting: bool = False
    ):
        """Initialize STM Mean Reversion strategy."""
        self.name = name
        
        # Bollinger Bands
        self.bb_period = bb_period
        self.bb_std_dev = bb_std_dev
        self.price_below_bb_threshold = price_below_bb_threshold
        
        # RSI
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_exit_threshold = rsi_exit_threshold
        
        # Volume
        self.volume_period = volume_period
        self.volume_surge_ratio = volume_surge_ratio
        
        # Quality Filters
        self.min_price = min_price
        self.max_price = max_price
        self.min_avg_volume = min_avg_volume
        self.min_market_cap = min_market_cap
        
        # Earnings
        self.avoid_earnings = avoid_earnings
        self.days_before_earnings = days_before_earnings
        self.days_after_earnings = days_after_earnings
        
        # Exit Rules
        self.exit_at_bb_middle = exit_at_bb_middle
        self.exit_at_rsi_threshold = exit_at_rsi_threshold
        self.max_hold_days = max_hold_days
        
        # Risk
        self.stop_loss_pct = stop_loss_pct
        self.trailing_stop_pct = trailing_stop_pct
        self.use_trailing_stop = use_trailing_stop
        
        # Position Sizing
        self.risk_per_trade_pct = risk_per_trade_pct
        self.max_position_pct = max_position_pct
        self.use_atr_sizing = use_atr_sizing
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier
        
        # Portfolio
        self.max_concurrent_positions = max_concurrent_positions
        self.equal_weighting = equal_weighting
        
        # State tracking
        self.open_positions = {}
        self.closed_trades = []
        self.entry_dates = {}
        self.stop_prices = {}
        self.trailing_stops = {}
    
    def get_required_indicators(self) -> List[str]:
        """Return list of required indicators."""
        return [
            f'bb_upper_{self.bb_period}_{self.bb_std_dev}',
            f'bb_middle_{self.bb_period}_{self.bb_std_dev}',
            f'bb_lower_{self.bb_period}_{self.bb_std_dev}',
            f'rsi_{self.rsi_period}',
            f'atr_{self.atr_period}',
            f'sma_{self.volume_period}'  # For volume average
        ]
    
    def passes_quality_filters(
        self,
        price: float,
        avg_volume: float,
        market_cap: Optional[float] = None
    ) -> bool:
        """
        Check if stock passes quality filters.
        
        Args:
            price: Current stock price
            avg_volume: Average daily volume
            market_cap: Market capitalization (optional)
            
        Returns:
            True if passes all filters
        """
        # Price range
        if price < self.min_price or price > self.max_price:
            return False
        
        # Volume
        if avg_volume < self.min_avg_volume:
            return False
        
        # Market cap (if available)
        if market_cap is not None and market_cap < self.min_market_cap:
            return False
        
        return True
    
    def is_near_earnings(
        self,
        current_date: datetime,
        earnings_date: Optional[datetime]
    ) -> bool:
        """
        Check if current date is too close to earnings.
        
        Args:
            current_date: Current date
            earnings_date: Next earnings announcement date
            
        Returns:
            True if too close to earnings
        """
        if not self.avoid_earnings or earnings_date is None:
            return False
        
        days_until_earnings = (earnings_date - current_date).days
        
        # Too close before earnings
        if 0 <= days_until_earnings <= self.days_before_earnings:
            return True
        
        # Too close after earnings
        if -self.days_after_earnings <= days_until_earnings < 0:
            return True
        
        return False
    
    def generate_entry_signals(
        self,
        data: pd.DataFrame,
        earnings_dates: Optional[Dict[datetime, datetime]] = None
    ) -> pd.Series:
        """
        Generate entry signals for STM strategy.
        
        Args:
            data: DataFrame with OHLCV and indicators
            earnings_dates: Dict mapping dates to next earnings date
            
        Returns:
            Series with 1 for BUY signal, 0 for no signal
        """
        signals = pd.Series(0, index=data.index)
        
        # Get indicator columns
        bb_lower_col = f'bb_lower_{self.bb_period}_{self.bb_std_dev}'
        bb_middle_col = f'bb_middle_{self.bb_period}_{self.bb_std_dev}'
        rsi_col = f'rsi_{self.rsi_period}'
        
        # Calculate average volume
        avg_volume = data['volume'].rolling(window=self.volume_period).mean()
        
        # Entry conditions
        for idx in data.index:
            row = data.loc[idx]
            
            # Quality filters
            if not self.passes_quality_filters(
                price=row['close'],
                avg_volume=avg_volume.loc[idx] if idx in avg_volume.index else 0
            ):
                continue
            
            # Earnings check
            if earnings_dates and idx in earnings_dates:
                if self.is_near_earnings(idx, earnings_dates[idx]):
                    continue
            
            # 1. Price below lower Bollinger Band
            price_below_bb = row['close'] < (row[bb_lower_col] * (1 - self.price_below_bb_threshold))
            
            # 2. RSI oversold
            rsi_oversold = row[rsi_col] < self.rsi_oversold
            
            # 3. Volume spike
            volume_spike = row['volume'] > (avg_volume.loc[idx] * self.volume_surge_ratio)
            
            # All conditions must be met
            if price_below_bb and rsi_oversold and volume_spike:
                signals.loc[idx] = 1
        
        return signals
    
    def generate_exit_signals(
        self,
        data: pd.DataFrame,
        symbol: str,
        entry_date: datetime,
        entry_price: float,
        current_date: datetime
    ) -> Tuple[bool, str]:
        """
        Check if position should be exited.
        
        Args:
            data: DataFrame with OHLCV and indicators
            symbol: Stock symbol
            entry_date: Date position was entered
            entry_price: Entry price
            current_date: Current date
            
        Returns:
            Tuple of (should_exit, exit_reason)
        """
        if current_date not in data.index:
            return False, ""
        
        row = data.loc[current_date]
        
        bb_middle_col = f'bb_middle_{self.bb_period}_{self.bb_std_dev}'
        rsi_col = f'rsi_{self.rsi_period}'
        
        # 1. Stop-loss check
        stop_price = entry_price * (1 - self.stop_loss_pct)
        if symbol in self.trailing_stops:
            stop_price = self.trailing_stops[symbol]
        
        if row['low'] <= stop_price:
            return True, "Stop Loss"
        
        # 2. Maximum hold period
        days_held = (current_date - entry_date).days
        if days_held >= self.max_hold_days:
            return True, f"Max Hold ({self.max_hold_days} days)"
        
        # 3. Price at BB middle (take profit)
        if self.exit_at_bb_middle:
            if row['close'] >= row[bb_middle_col]:
                return True, "BB Middle (Take Profit)"
        
        # 4. RSI exit threshold
        if self.exit_at_rsi_threshold:
            if row[rsi_col] > self.rsi_exit_threshold:
                return True, f"RSI > {self.rsi_exit_threshold}"
        
        # 5. Update trailing stop
        if self.use_trailing_stop:
            highest_since_entry = data.loc[entry_date:current_date, 'high'].max()
            new_trailing_stop = highest_since_entry * (1 - self.trailing_stop_pct)
            if symbol not in self.trailing_stops or new_trailing_stop > self.trailing_stops[symbol]:
                self.trailing_stops[symbol] = new_trailing_stop
        
        return False, ""
    
    def calculate_position_size(
        self,
        capital: float,
        entry_price: float,
        atr: Optional[float] = None
    ) -> int:
        """
        Calculate number of shares to buy.
        
        Args:
            capital: Available capital
            entry_price: Entry price per share
            atr: Average True Range (for ATR-based sizing)
            
        Returns:
            Number of shares to buy
        """
        if self.use_atr_sizing and atr is not None and atr > 0:
            # ATR-based position sizing
            # Risk amount = capital * risk_per_trade
            # Position size = risk_amount / (ATR * multiplier)
            risk_amount = capital * self.risk_per_trade_pct
            stop_distance = atr * self.atr_multiplier
            shares = int(risk_amount / stop_distance)
        else:
            # Fixed percentage position sizing
            position_value = capital * self.max_position_pct
            shares = int(position_value / entry_price)
        
        # Ensure position doesn't exceed max percentage
        max_shares = int((capital * self.max_position_pct) / entry_price)
        shares = min(shares, max_shares)
        
        return max(shares, 0)
    
    def get_parameters(self) -> Dict:
        """Get strategy parameters for logging."""
        return {
            'name': self.name,
            'bb_period': self.bb_period,
            'bb_std_dev': self.bb_std_dev,
            'rsi_period': self.rsi_period,
            'rsi_oversold': self.rsi_oversold,
            'rsi_exit_threshold': self.rsi_exit_threshold,
            'volume_surge_ratio': self.volume_surge_ratio,
            'stop_loss_pct': self.stop_loss_pct,
            'trailing_stop_pct': self.trailing_stop_pct,
            'max_hold_days': self.max_hold_days,
            'risk_per_trade_pct': self.risk_per_trade_pct,
            'max_concurrent_positions': self.max_concurrent_positions,
            'min_price': self.min_price,
            'max_price': self.max_price,
            'min_avg_volume': self.min_avg_volume,
        }
    
    def __repr__(self) -> str:
        return f"<STM_MeanReversion: {self.name}>"


# Preset configurations
def get_conservative_stm_params() -> Dict:
    """Conservative STM parameters for lower risk."""
    return {
        'rsi_oversold': 25,  # More selective
        'volume_surge_ratio': 2.0,  # Stronger confirmation
        'stop_loss_pct': 0.04,  # Tighter stop (4%)
        'risk_per_trade_pct': 0.015,  # Lower risk (1.5%)
        'max_concurrent_positions': 5,  # Fewer positions
        'max_hold_days': 3,  # Shorter holds
    }


def get_aggressive_stm_params() -> Dict:
    """Aggressive STM parameters for higher returns."""
    return {
        'rsi_oversold': 35,  # More frequent entries
        'volume_surge_ratio': 1.3,  # Less strict
        'stop_loss_pct': 0.06,  # Wider stop (6%)
        'risk_per_trade_pct': 0.025,  # Higher risk (2.5%)
        'max_concurrent_positions': 10,  # More positions
        'max_hold_days': 7,  # Longer holds
    }


def get_scalping_stm_params() -> Dict:
    """Ultra-short-term scalping parameters."""
    return {
        'bb_period': 10,  # Faster BB
        'rsi_period': 7,  # Faster RSI
        'rsi_oversold': 20,  # Extreme oversold
        'volume_surge_ratio': 2.5,  # Strong volume
        'stop_loss_pct': 0.03,  # Tight stop (3%)
        'max_hold_days': 2,  # Very short holds
        'risk_per_trade_pct': 0.01,  # Small risk
    }
