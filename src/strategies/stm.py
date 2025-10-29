"""
STM (Short-Term Mean Reversion) Strategy for AlphaFactory OS
CORRECTED VERSION - Uses your actual indicator column names

Phase 1: Primary Profit Generator
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta


class STM_MeanReversion:
    """
    Short-Term Mean Reversion Strategy
    
    Designed for 1-5 day holds with high win rate.
    Trades oversold bounces back to mean.
    """
    
    def __init__(
        self,
        # Entry parameters
        rsi_oversold: float = 30,
        rsi_exit_threshold: float = 50,
        volume_surge_ratio: float = 1.5,
        volume_lookback: int = 20,
        price_below_bb_threshold: float = 0.01,  # 1% below lower BB
        
        # Quality filters
        min_price: float = 10.0,
        max_price: float = 500.0,
        min_avg_volume: int = 500000,
        min_market_cap: float = 1e9,  # $1B
        
        # Earnings avoidance
        avoid_earnings: bool = True,
        days_before_earnings: int = 5,
        days_after_earnings: int = 2,
        
        # Exit rules
        exit_at_bb_middle: bool = True,
        exit_at_rsi_threshold: bool = True,
        max_hold_days: int = 5,
        
        # Risk management
        stop_loss_pct: float = 0.05,  # 5%
        trailing_stop_pct: float = 0.02,  # 2%
        use_trailing_stop: bool = True,
        
        # Position sizing
        risk_per_trade_pct: float = 0.02,  # 2%
        max_position_pct: float = 0.10,  # 10%
        use_atr_sizing: bool = True,
        atr_multiplier: float = 2.5,
        
        # Portfolio
        max_concurrent_positions: int = 10,
    ):
        """Initialize STM Mean Reversion strategy."""
        self.name = "STM_MeanReversion"
        
        # Entry
        self.rsi_oversold = rsi_oversold
        self.rsi_exit_threshold = rsi_exit_threshold
        self.volume_surge_ratio = volume_surge_ratio
        self.volume_lookback = volume_lookback
        self.price_below_bb_threshold = price_below_bb_threshold
        
        # Quality
        self.min_price = min_price
        self.max_price = max_price
        self.min_avg_volume = min_avg_volume
        self.min_market_cap = min_market_cap
        
        # Earnings
        self.avoid_earnings = avoid_earnings
        self.days_before_earnings = days_before_earnings
        self.days_after_earnings = days_after_earnings
        
        # Exit
        self.exit_at_bb_middle = exit_at_bb_middle
        self.exit_at_rsi_threshold = exit_at_rsi_threshold
        self.max_hold_days = max_hold_days
        
        # Risk
        self.stop_loss_pct = stop_loss_pct
        self.trailing_stop_pct = trailing_stop_pct
        self.use_trailing_stop = use_trailing_stop
        
        # Position sizing
        self.risk_per_trade_pct = risk_per_trade_pct
        self.max_position_pct = max_position_pct
        self.use_atr_sizing = use_atr_sizing
        self.atr_multiplier = atr_multiplier
        
        # Portfolio
        self.max_concurrent_positions = max_concurrent_positions
        
        # State tracking
        self.open_positions = {}
        self.closed_trades = []
        self.trailing_stops = {}
    
    def get_required_indicators(self) -> List[str]:
        """Return list of required indicators (using your actual column names)."""
        return [
            'bb_upper',
            'bb_middle',
            'bb_lower',
            'rsi_14',
            'atr_14',
        ]
    
    def passes_quality_filters(
        self,
        price: float,
        avg_volume: float,
        market_cap: Optional[float] = None
    ) -> bool:
        """Check if stock passes quality filters."""
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
        """Check if current date is too close to earnings."""
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
        
        # Calculate average volume
        avg_volume = data['volume'].rolling(window=self.volume_lookback).mean()
        
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
            price_below_bb = row['close'] < (row['bb_lower'] * (1 - self.price_below_bb_threshold))
            
            # 2. RSI oversold
            rsi_oversold = row['rsi_14'] < self.rsi_oversold
            
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
        
        Returns:
            Tuple of (should_exit, exit_reason)
        """
        if current_date not in data.index:
            return False, ""
        
        row = data.loc[current_date]
        
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
            if row['close'] >= row['bb_middle']:
                return True, "BB Middle (Take Profit)"
        
        # 4. RSI exit threshold
        if self.exit_at_rsi_threshold:
            if row['rsi_14'] > self.rsi_exit_threshold:
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
        'rsi_oversold': 20,  # Extreme oversold
        'volume_surge_ratio': 2.5,  # Strong volume
        'stop_loss_pct': 0.03,  # Tight stop (3%)
        'max_hold_days': 2,  # Very short holds
        'risk_per_trade_pct': 0.01,  # Small risk
    }
