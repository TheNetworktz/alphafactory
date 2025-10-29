"""
Bollinger Bands Mean Reversion Strategy
Package #3: Advanced Strategies

Strategy Logic:
- LONG Entry: Price touches/breaks lower BB + Volume spike + RSI not overbought
- SHORT Entry: Price touches/breaks upper BB + Volume spike + RSI not oversold
- Exit: Price reaches middle BB OR opposite signal OR stops hit

Classic mean reversion strategy that profits from price returning to the mean.
"""

import pandas as pd
import numpy as np
from typing import List
from strategy_base import AdvancedStrategy, SignalType, PositionSizingMethod


class BollingerBandsMeanReversion(AdvancedStrategy):
    """
    Mean reversion strategy using Bollinger Bands.
    """
    
    def __init__(
        self,
        bb_period: int = 20,
        bb_std: float = 2.0,
        rsi_period: int = 14,
        rsi_extreme_high: float = 80,
        rsi_extreme_low: float = 20,
        volume_surge_ratio: float = 1.5,
        exit_at_middle_band: bool = True,
        require_bb_squeeze: bool = False,
        squeeze_threshold: float = 0.02,
        **kwargs
    ):
        """
        Initialize Bollinger Bands mean reversion strategy.
        
        Args:
            bb_period: Bollinger Bands moving average period
            bb_std: Standard deviation multiplier
            rsi_period: RSI period for confirmation
            rsi_extreme_high: RSI upper threshold
            rsi_extreme_low: RSI lower threshold
            volume_surge_ratio: Volume vs. average ratio for confirmation
            exit_at_middle_band: Exit when price reaches middle band
            require_bb_squeeze: Only trade after BB squeeze
            squeeze_threshold: Threshold for identifying squeeze
            **kwargs: Additional parameters
        """
        super().__init__(
            name=f"BB_MeanReversion_{bb_period}_{bb_std}std",
            **kwargs
        )
        
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.rsi_period = rsi_period
        self.rsi_extreme_high = rsi_extreme_high
        self.rsi_extreme_low = rsi_extreme_low
        self.volume_surge_ratio = volume_surge_ratio
        self.exit_at_middle_band = exit_at_middle_band
        self.require_bb_squeeze = require_bb_squeeze
        self.squeeze_threshold = squeeze_threshold
        
        self.parameters.update({
            'bb_period': bb_period,
            'bb_std': bb_std,
            'rsi_period': rsi_period,
            'rsi_extreme_high': rsi_extreme_high,
            'rsi_extreme_low': rsi_extreme_low,
            'volume_surge_ratio': volume_surge_ratio,
            'exit_at_middle_band': exit_at_middle_band,
            'require_bb_squeeze': require_bb_squeeze,
            'squeeze_threshold': squeeze_threshold,
        })
    
    def get_required_indicators(self) -> List[str]:
        """Return required indicators."""
        return [
            f'bb_upper_{self.bb_period}_{self.bb_std}',
            f'bb_middle_{self.bb_period}_{self.bb_std}',
            f'bb_lower_{self.bb_period}_{self.bb_std}',
            f'rsi_{self.rsi_period}',
        ]
    
    def _detect_bb_squeeze(self, data: pd.DataFrame) -> pd.Series:
        """
        Detect Bollinger Band squeeze (low volatility periods).
        
        Args:
            data: DataFrame with BB indicators
            
        Returns:
            Boolean series indicating squeeze conditions
        """
        upper_col = f'bb_upper_{self.bb_period}_{self.bb_std}'
        lower_col = f'bb_lower_{self.bb_period}_{self.bb_std}'
        middle_col = f'bb_middle_{self.bb_period}_{self.bb_std}'
        
        # BB width as percentage of middle band
        bb_width = (data[upper_col] - data[lower_col]) / data[middle_col]
        
        # Squeeze = BB width narrower than threshold
        squeeze = bb_width < self.squeeze_threshold
        
        # Also check if width is narrowest in recent period
        narrowest = bb_width == bb_width.rolling(20).min()
        
        return squeeze | narrowest
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """
        Generate mean reversion signals based on BB touches.
        
        Args:
            data: DataFrame with OHLCV and indicators
            
        Returns:
            Series with signals: 1 (LONG), -1 (SHORT), 0 (NEUTRAL)
        """
        self.validate_data(data)
        
        signals = pd.Series(0, index=data.index)
        
        # Get indicator columns
        upper_col = f'bb_upper_{self.bb_period}_{self.bb_std}'
        middle_col = f'bb_middle_{self.bb_period}_{self.bb_std}'
        lower_col = f'bb_lower_{self.bb_period}_{self.bb_std}'
        rsi_col = f'rsi_{self.rsi_period}'
        
        upper_bb = data[upper_col]
        middle_bb = data[middle_col]
        lower_bb = data[lower_col]
        rsi = data[rsi_col]
        
        # Volume surge detection
        avg_volume = data['volume'].rolling(window=20).mean()
        volume_surge = data['volume'] > (avg_volume * self.volume_surge_ratio)
        
        # Price touching/breaking BB bands
        touch_lower = (data['low'] <= lower_bb) | (data['close'] <= lower_bb)
        touch_upper = (data['high'] >= upper_bb) | (data['close'] >= upper_bb)
        
        # Check for BB squeeze if required
        if self.require_bb_squeeze:
            squeeze_detected = self._detect_bb_squeeze(data)
            # Wait for squeeze to end (expansion)
            squeeze_ended = squeeze_detected.shift(1) & ~squeeze_detected
        else:
            squeeze_ended = pd.Series(True, index=data.index)
        
        # LONG conditions: Touch lower BB + volume surge + RSI not extreme
        long_conditions = (
            touch_lower &
            volume_surge &
            (rsi < self.rsi_extreme_high) &  # Not overbought
            squeeze_ended
        )
        
        # SHORT conditions: Touch upper BB + volume surge + RSI not extreme
        short_conditions = (
            touch_upper &
            volume_surge &
            (rsi > self.rsi_extreme_low) &  # Not oversold
            squeeze_ended
        )
        
        # Set signals
        signals[long_conditions] = 1
        signals[short_conditions] = -1
        
        # Generate exit signals if using middle band exits
        if self.exit_at_middle_band:
            # Exit long when price crosses above middle band
            exit_long = (data['close'] >= middle_bb) & (data['close'].shift(1) < middle_bb.shift(1))
            signals[exit_long] = 2  # EXIT_LONG signal
            
            # Exit short when price crosses below middle band
            exit_short = (data['close'] <= middle_bb) & (data['close'].shift(1) > middle_bb.shift(1))
            signals[exit_short] = -2  # EXIT_SHORT signal
        
        return signals


class BollingerBandBreakout(AdvancedStrategy):
    """
    Bollinger Band breakout strategy (opposite of mean reversion).
    
    Trades breakouts from BB bands, betting on trend continuation.
    """
    
    def __init__(
        self,
        bb_period: int = 20,
        bb_std: float = 2.0,
        volume_surge_ratio: float = 2.0,
        min_adx: float = 25,
        require_squeeze_setup: bool = True,
        **kwargs
    ):
        """
        Initialize BB breakout strategy.
        
        Args:
            bb_period: Bollinger Bands period
            bb_std: Standard deviation multiplier
            volume_surge_ratio: Required volume surge
            min_adx: Minimum ADX for trend strength
            require_squeeze_setup: Require BB squeeze before breakout
            **kwargs: Additional parameters
        """
        super().__init__(
            name=f"BB_Breakout_{bb_period}_{bb_std}std",
            **kwargs
        )
        
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.volume_surge_ratio = volume_surge_ratio
        self.min_adx = min_adx
        self.require_squeeze_setup = require_squeeze_setup
        
        self.parameters.update({
            'bb_period': bb_period,
            'bb_std': bb_std,
            'volume_surge_ratio': volume_surge_ratio,
            'min_adx': min_adx,
            'require_squeeze_setup': require_squeeze_setup,
        })
    
    def get_required_indicators(self) -> List[str]:
        """Return required indicators."""
        return [
            f'bb_upper_{self.bb_period}_{self.bb_std}',
            f'bb_middle_{self.bb_period}_{self.bb_std}',
            f'bb_lower_{self.bb_period}_{self.bb_std}',
            'adx_14',
        ]
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """
        Generate breakout signals.
        
        Args:
            data: DataFrame with OHLCV and indicators
            
        Returns:
            Series with signals
        """
        self.validate_data(data)
        
        signals = pd.Series(0, index=data.index)
        
        # Get indicator columns
        upper_col = f'bb_upper_{self.bb_period}_{self.bb_std}'
        lower_col = f'bb_lower_{self.bb_period}_{self.bb_std}'
        middle_col = f'bb_middle_{self.bb_period}_{self.bb_std}'
        
        upper_bb = data[upper_col]
        lower_bb = data[lower_col]
        middle_bb = data[middle_col]
        
        # Volume surge
        avg_volume = data['volume'].rolling(window=20).mean()
        volume_surge = data['volume'] > (avg_volume * self.volume_surge_ratio)
        
        # ADX for trend strength
        strong_trend = data['adx_14'] > self.min_adx
        
        # Breakout detection: Close ABOVE upper band or BELOW lower band
        breakout_above = (
            (data['close'] > upper_bb) &
            (data['close'].shift(1) <= upper_bb.shift(1))
        )
        
        breakout_below = (
            (data['close'] < lower_bb) &
            (data['close'].shift(1) >= lower_bb.shift(1))
        )
        
        # LONG on upside breakout
        long_conditions = breakout_above & volume_surge & strong_trend
        
        # SHORT on downside breakout
        short_conditions = breakout_below & volume_surge & strong_trend
        
        signals[long_conditions] = 1
        signals[short_conditions] = -1
        
        return signals


class BollingerBandCombo(AdvancedStrategy):
    """
    Combination strategy: Mean reversion in range, breakout in trend.
    
    Uses ADX to determine market regime:
    - Low ADX (<20): Mean reversion mode
    - High ADX (>30): Breakout mode
    """
    
    def __init__(
        self,
        bb_period: int = 20,
        bb_std: float = 2.0,
        adx_ranging_threshold: float = 20,
        adx_trending_threshold: float = 30,
        **kwargs
    ):
        """
        Initialize combination strategy.
        
        Args:
            bb_period: Bollinger Bands period
            bb_std: Standard deviation multiplier
            adx_ranging_threshold: ADX below this = ranging market
            adx_trending_threshold: ADX above this = trending market
            **kwargs: Additional parameters
        """
        super().__init__(
            name=f"BB_Combo_{bb_period}_{bb_std}std",
            **kwargs
        )
        
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.adx_ranging_threshold = adx_ranging_threshold
        self.adx_trending_threshold = adx_trending_threshold
        
        self.parameters.update({
            'bb_period': bb_period,
            'bb_std': bb_std,
            'adx_ranging_threshold': adx_ranging_threshold,
            'adx_trending_threshold': adx_trending_threshold,
        })
    
    def get_required_indicators(self) -> List[str]:
        """Return required indicators."""
        return [
            f'bb_upper_{self.bb_period}_{self.bb_std}',
            f'bb_middle_{self.bb_period}_{self.bb_std}',
            f'bb_lower_{self.bb_period}_{self.bb_std}',
            'adx_14',
            'rsi_14',
        ]
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """
        Generate adaptive signals based on market regime.
        
        Args:
            data: DataFrame with OHLCV and indicators
            
        Returns:
            Series with signals
        """
        self.validate_data(data)
        
        signals = pd.Series(0, index=data.index)
        
        # Get columns
        upper_col = f'bb_upper_{self.bb_period}_{self.bb_std}'
        middle_col = f'bb_middle_{self.bb_period}_{self.bb_std}'
        lower_col = f'bb_lower_{self.bb_period}_{self.bb_std}'
        
        upper_bb = data[upper_col]
        middle_bb = data[middle_col]
        lower_bb = data[lower_col]
        adx = data['adx_14']
        rsi = data['rsi_14']
        
        # Identify market regime
        ranging_market = adx < self.adx_ranging_threshold
        trending_market = adx > self.adx_trending_threshold
        
        # Mean reversion signals (for ranging markets)
        touch_lower = data['low'] <= lower_bb
        touch_upper = data['high'] >= upper_bb
        
        mean_reversion_long = ranging_market & touch_lower & (rsi < 70)
        mean_reversion_short = ranging_market & touch_upper & (rsi > 30)
        
        # Breakout signals (for trending markets)
        breakout_above = (data['close'] > upper_bb) & (data['close'].shift(1) <= upper_bb.shift(1))
        breakout_below = (data['close'] < lower_bb) & (data['close'].shift(1) >= lower_bb.shift(1))
        
        breakout_long = trending_market & breakout_above
        breakout_short = trending_market & breakout_below
        
        # Combine signals
        signals[mean_reversion_long | breakout_long] = 1
        signals[mean_reversion_short | breakout_short] = -1
        
        return signals
