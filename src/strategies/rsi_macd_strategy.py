"""
RSI + MACD Combination Strategy
Package #3: Advanced Strategies

Strategy Logic:
- LONG Entry: RSI < 30 (oversold) AND MACD crosses above signal line
- SHORT Entry: RSI > 70 (overbought) AND MACD crosses below signal line
- Exit: Opposite signal OR stop-loss/take-profit hit

This strategy looks for confluence between mean reversion (RSI) 
and momentum (MACD) for higher probability trades.
"""

import pandas as pd
import numpy as np
from typing import List
from strategy_base import AdvancedStrategy, SignalType, PositionSizingMethod


class RSI_MACD_Strategy(AdvancedStrategy):
    """
    Combined RSI and MACD strategy looking for confluence signals.
    """
    
    def __init__(
        self,
        rsi_period: int = 14,
        rsi_oversold: float = 30,
        rsi_overbought: float = 70,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        require_macd_histogram_positive: bool = True,
        volume_filter: bool = True,
        min_volume_ratio: float = 1.2,
        **kwargs
    ):
        """
        Initialize RSI + MACD strategy.
        
        Args:
            rsi_period: RSI calculation period
            rsi_oversold: RSI oversold threshold
            rsi_overbought: RSI overbought threshold
            macd_fast: MACD fast EMA period
            macd_slow: MACD slow EMA period
            macd_signal: MACD signal line period
            require_macd_histogram_positive: Require MACD histogram > 0 for longs
            volume_filter: Apply volume filter
            min_volume_ratio: Minimum volume vs. average ratio
            **kwargs: Additional parameters passed to AdvancedStrategy
        """
        super().__init__(
            name=f"RSI{rsi_period}_MACD({macd_fast},{macd_slow},{macd_signal})",
            **kwargs
        )
        
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.require_macd_histogram_positive = require_macd_histogram_positive
        self.volume_filter = volume_filter
        self.min_volume_ratio = min_volume_ratio
        
        # Store in parameters dict
        self.parameters.update({
            'rsi_period': rsi_period,
            'rsi_oversold': rsi_oversold,
            'rsi_overbought': rsi_overbought,
            'macd_fast': macd_fast,
            'macd_slow': macd_slow,
            'macd_signal': macd_signal,
            'require_macd_histogram_positive': require_macd_histogram_positive,
            'volume_filter': volume_filter,
            'min_volume_ratio': min_volume_ratio,
        })
    
    def get_required_indicators(self) -> List[str]:
        """Return required indicators."""
        return [
            f'rsi_{self.rsi_period}',
            f'macd_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}',
            f'macd_signal_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}',
            f'macd_hist_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}',
            'sma_20'  # For volume filter
        ]
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """
        Generate trading signals based on RSI + MACD confluence.
        
        Args:
            data: DataFrame with OHLCV and indicators
            
        Returns:
            Series with signals: 1 (LONG), -1 (SHORT), 0 (NEUTRAL)
        """
        self.validate_data(data)
        
        signals = pd.Series(0, index=data.index)
        
        # Get indicator columns
        rsi_col = f'rsi_{self.rsi_period}'
        macd_col = f'macd_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}'
        macd_signal_col = f'macd_signal_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}'
        macd_hist_col = f'macd_hist_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}'
        
        rsi = data[rsi_col]
        macd = data[macd_col]
        macd_signal = data[macd_signal_col]
        macd_hist = data[macd_hist_col]
        
        # Calculate MACD crossovers
        macd_cross_above = (macd > macd_signal) & (macd.shift(1) <= macd_signal.shift(1))
        macd_cross_below = (macd < macd_signal) & (macd.shift(1) >= macd_signal.shift(1))
        
        # LONG conditions: RSI oversold + MACD bullish cross
        long_conditions = (
            (rsi < self.rsi_oversold) &
            macd_cross_above
        )
        
        if self.require_macd_histogram_positive:
            long_conditions = long_conditions & (macd_hist > 0)
        
        # SHORT conditions: RSI overbought + MACD bearish cross
        short_conditions = (
            (rsi > self.rsi_overbought) &
            macd_cross_below
        )
        
        if self.require_macd_histogram_positive:
            short_conditions = short_conditions & (macd_hist < 0)
        
        # Set signals
        signals[long_conditions] = 1
        signals[short_conditions] = -1
        
        return signals
    
    def apply_filters(self, data: pd.DataFrame, signals: pd.Series) -> pd.Series:
        """
        Apply volume filter if enabled.
        
        Args:
            data: DataFrame with market data
            signals: Raw signals
            
        Returns:
            Filtered signals
        """
        if not self.volume_filter:
            return signals
        
        filtered_signals = signals.copy()
        
        # Calculate volume ratio vs 20-day average
        if 'volume' in data.columns and 'sma_20' in data.columns:
            avg_volume = data['volume'].rolling(window=20).mean()
            volume_ratio = data['volume'] / avg_volume
            
            # Only take signals when volume is above threshold
            low_volume_mask = volume_ratio < self.min_volume_ratio
            filtered_signals[low_volume_mask] = 0
        
        return filtered_signals


class RSI_MACD_Enhanced_Strategy(RSI_MACD_Strategy):
    """
    Enhanced version with additional confirmation filters.
    
    Adds:
    - Trend filter (only trade in direction of longer-term trend)
    - ADX filter (only trade when trend strength is adequate)
    - Support/resistance awareness
    """
    
    def __init__(
        self,
        use_trend_filter: bool = True,
        trend_sma_period: int = 200,
        use_adx_filter: bool = True,
        min_adx: float = 25,
        **kwargs
    ):
        """
        Initialize enhanced RSI + MACD strategy.
        
        Args:
            use_trend_filter: Only trade in direction of longer-term trend
            trend_sma_period: SMA period for trend determination
            use_adx_filter: Require minimum ADX for trend strength
            min_adx: Minimum ADX value
            **kwargs: Additional parameters
        """
        super().__init__(**kwargs)
        
        self.use_trend_filter = use_trend_filter
        self.trend_sma_period = trend_sma_period
        self.use_adx_filter = use_adx_filter
        self.min_adx = min_adx
        
        self.name = f"RSI_MACD_Enhanced_{self.rsi_period}"
        
        self.parameters.update({
            'use_trend_filter': use_trend_filter,
            'trend_sma_period': trend_sma_period,
            'use_adx_filter': use_adx_filter,
            'min_adx': min_adx,
        })
    
    def get_required_indicators(self) -> List[str]:
        """Return required indicators including additional filters."""
        indicators = super().get_required_indicators()
        
        if self.use_trend_filter:
            indicators.append(f'sma_{self.trend_sma_period}')
        
        if self.use_adx_filter:
            indicators.append('adx_14')
        
        return indicators
    
    def apply_filters(self, data: pd.DataFrame, signals: pd.Series) -> pd.Series:
        """
        Apply enhanced filters including trend and ADX.
        
        Args:
            data: DataFrame with market data
            signals: Raw signals
            
        Returns:
            Filtered signals
        """
        # First apply parent volume filter
        filtered_signals = super().apply_filters(data, signals)
        
        # Trend filter: only long above SMA, only short below SMA
        if self.use_trend_filter:
            trend_sma_col = f'sma_{self.trend_sma_period}'
            if trend_sma_col in data.columns:
                # Cancel long signals below trend SMA
                below_trend = data['close'] < data[trend_sma_col]
                filtered_signals[below_trend & (filtered_signals == 1)] = 0
                
                # Cancel short signals above trend SMA
                above_trend = data['close'] > data[trend_sma_col]
                filtered_signals[above_trend & (filtered_signals == -1)] = 0
        
        # ADX filter: only trade when trend is strong enough
        if self.use_adx_filter and 'adx_14' in data.columns:
            weak_trend = data['adx_14'] < self.min_adx
            filtered_signals[weak_trend] = 0
        
        return filtered_signals


# Example usage and parameter sets
def get_conservative_params() -> dict:
    """Conservative parameter set for lower risk."""
    return {
        'rsi_oversold': 25,
        'rsi_overbought': 75,
        'stop_loss_pct': 0.02,
        'take_profit_pct': 0.06,
        'trailing_stop_pct': 0.015,
        'position_size_pct': 0.05,
        'risk_per_trade': 0.01,
    }


def get_aggressive_params() -> dict:
    """Aggressive parameter set for higher risk/reward."""
    return {
        'rsi_oversold': 35,
        'rsi_overbought': 65,
        'stop_loss_pct': 0.03,
        'take_profit_pct': 0.10,
        'trailing_stop_pct': 0.02,
        'position_size_pct': 0.15,
        'risk_per_trade': 0.025,
    }


def get_scalping_params() -> dict:
    """Scalping parameter set for quick trades."""
    return {
        'rsi_period': 7,
        'rsi_oversold': 20,
        'rsi_overbought': 80,
        'macd_fast': 8,
        'macd_slow': 17,
        'macd_signal': 9,
        'stop_loss_pct': 0.01,
        'take_profit_pct': 0.02,
        'volume_filter': True,
        'min_volume_ratio': 1.5,
    }
