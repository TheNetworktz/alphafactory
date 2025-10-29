"""
Advanced Strategy Base Class for AlphaFactory OS
Package #3: Advanced Strategies & Optimization

This base class extends the simple strategy framework with:
- Risk management (stop-loss, take-profit)
- Position sizing algorithms
- Multi-indicator support
- Entry/exit rules separation
- Trade management logic
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from enum import Enum


class PositionSizingMethod(Enum):
    """Position sizing algorithms"""
    FIXED = "fixed"
    VOLATILITY_ATR = "volatility_atr"
    KELLY_CRITERION = "kelly_criterion"
    FIXED_FRACTIONAL = "fixed_fractional"
    EQUAL_WEIGHT = "equal_weight"


class SignalType(Enum):
    """Trading signal types"""
    LONG = 1
    SHORT = -1
    NEUTRAL = 0
    EXIT_LONG = 2
    EXIT_SHORT = -2


class AdvancedStrategy(ABC):
    """
    Advanced base class for trading strategies with risk management
    and sophisticated position sizing.
    """
    
    def __init__(
        self,
        name: str,
        initial_capital: float = 100000.0,
        position_sizing_method: PositionSizingMethod = PositionSizingMethod.FIXED,
        position_size_pct: float = 0.1,
        max_position_size: float = 0.25,
        stop_loss_pct: Optional[float] = None,
        take_profit_pct: Optional[float] = None,
        trailing_stop_pct: Optional[float] = None,
        max_positions: int = 10,
        risk_per_trade: float = 0.02,
        use_atr_stops: bool = False,
        atr_stop_multiplier: float = 2.0,
        **kwargs
    ):
        """
        Initialize advanced strategy.
        
        Args:
            name: Strategy name
            initial_capital: Starting capital
            position_sizing_method: Algorithm for position sizing
            position_size_pct: Default position size as % of capital
            max_position_size: Maximum position size as % of capital
            stop_loss_pct: Stop loss percentage (e.g., 0.02 = 2%)
            take_profit_pct: Take profit percentage
            trailing_stop_pct: Trailing stop percentage
            max_positions: Maximum number of concurrent positions
            risk_per_trade: Maximum risk per trade as % of capital
            use_atr_stops: Use ATR-based stops instead of percentage
            atr_stop_multiplier: ATR multiplier for stop distance
            **kwargs: Additional strategy-specific parameters
        """
        self.name = name
        self.initial_capital = initial_capital
        self.position_sizing_method = position_sizing_method
        self.position_size_pct = position_size_pct
        self.max_position_size = max_position_size
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.trailing_stop_pct = trailing_stop_pct
        self.max_positions = max_positions
        self.risk_per_trade = risk_per_trade
        self.use_atr_stops = use_atr_stops
        self.atr_stop_multiplier = atr_stop_multiplier
        self.parameters = kwargs
        
        # Track positions and stops
        self.positions: Dict[str, Dict] = {}  # symbol -> position info
        self.stop_prices: Dict[str, float] = {}  # symbol -> stop price
        self.take_profit_prices: Dict[str, float] = {}  # symbol -> TP price
        
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """
        Generate trading signals based on strategy logic.
        
        Args:
            data: DataFrame with OHLCV data and indicators
            
        Returns:
            Series with signals: 1 (LONG), -1 (SHORT), 0 (NEUTRAL)
        """
        pass
    
    def calculate_position_size(
        self,
        symbol: str,
        price: float,
        equity: float,
        volatility: Optional[float] = None,
        win_rate: Optional[float] = None,
        avg_win_loss_ratio: Optional[float] = None
    ) -> float:
        """
        Calculate position size based on selected method.
        
        Args:
            symbol: Trading symbol
            price: Current price
            equity: Current account equity
            volatility: ATR or standard deviation for volatility-based sizing
            win_rate: Historical win rate for Kelly Criterion
            avg_win_loss_ratio: Average win/loss ratio for Kelly Criterion
            
        Returns:
            Number of shares to trade
        """
        if self.position_sizing_method == PositionSizingMethod.FIXED:
            position_value = equity * self.position_size_pct
            shares = position_value / price
            
        elif self.position_sizing_method == PositionSizingMethod.VOLATILITY_ATR:
            if volatility is None or volatility == 0:
                # Fallback to fixed sizing
                position_value = equity * self.position_size_pct
                shares = position_value / price
            else:
                # Risk-based position sizing using ATR
                risk_amount = equity * self.risk_per_trade
                stop_distance = volatility * self.atr_stop_multiplier
                shares = risk_amount / stop_distance if stop_distance > 0 else 0
                
        elif self.position_sizing_method == PositionSizingMethod.KELLY_CRITERION:
            if win_rate is not None and avg_win_loss_ratio is not None:
                # Kelly % = W - [(1-W) / R]
                # W = win rate, R = avg_win / avg_loss
                kelly_pct = win_rate - ((1 - win_rate) / avg_win_loss_ratio)
                kelly_pct = max(0, min(kelly_pct, 0.25))  # Cap at 25%
                # Use fractional Kelly (e.g., half Kelly)
                kelly_pct *= 0.5
                position_value = equity * kelly_pct
                shares = position_value / price
            else:
                # Fallback to fixed sizing
                position_value = equity * self.position_size_pct
                shares = position_value / price
                
        elif self.position_sizing_method == PositionSizingMethod.FIXED_FRACTIONAL:
            risk_amount = equity * self.risk_per_trade
            if self.stop_loss_pct:
                stop_distance = price * self.stop_loss_pct
                shares = risk_amount / stop_distance if stop_distance > 0 else 0
            else:
                position_value = equity * self.position_size_pct
                shares = position_value / price
                
        else:  # EQUAL_WEIGHT
            position_value = equity / self.max_positions
            shares = position_value / price
        
        # Apply maximum position size limit
        max_shares = (equity * self.max_position_size) / price
        shares = min(shares, max_shares)
        
        return int(shares)
    
    def calculate_stops(
        self,
        symbol: str,
        entry_price: float,
        signal: SignalType,
        atr: Optional[float] = None
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Calculate stop-loss and take-profit prices.
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price
            signal: Signal type (LONG or SHORT)
            atr: Average True Range for ATR-based stops
            
        Returns:
            Tuple of (stop_price, take_profit_price)
        """
        stop_price = None
        take_profit_price = None
        
        if signal == SignalType.LONG:
            # Long position stops
            if self.use_atr_stops and atr is not None:
                stop_price = entry_price - (atr * self.atr_stop_multiplier)
            elif self.stop_loss_pct:
                stop_price = entry_price * (1 - self.stop_loss_pct)
                
            if self.take_profit_pct:
                take_profit_price = entry_price * (1 + self.take_profit_pct)
                
        elif signal == SignalType.SHORT:
            # Short position stops
            if self.use_atr_stops and atr is not None:
                stop_price = entry_price + (atr * self.atr_stop_multiplier)
            elif self.stop_loss_pct:
                stop_price = entry_price * (1 + self.stop_loss_pct)
                
            if self.take_profit_pct:
                take_profit_price = entry_price * (1 - self.take_profit_pct)
        
        return stop_price, take_profit_price
    
    def update_trailing_stop(
        self,
        symbol: str,
        current_price: float,
        signal: SignalType
    ) -> Optional[float]:
        """
        Update trailing stop price if applicable.
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
            signal: Current position direction
            
        Returns:
            Updated stop price or None
        """
        if not self.trailing_stop_pct or symbol not in self.stop_prices:
            return None
            
        current_stop = self.stop_prices[symbol]
        
        if signal == SignalType.LONG:
            # For long positions, only move stop up
            new_stop = current_price * (1 - self.trailing_stop_pct)
            if new_stop > current_stop:
                return new_stop
                
        elif signal == SignalType.SHORT:
            # For short positions, only move stop down
            new_stop = current_price * (1 + self.trailing_stop_pct)
            if new_stop < current_stop:
                return new_stop
        
        return current_stop
    
    def check_exit_conditions(
        self,
        symbol: str,
        current_price: float,
        high: float,
        low: float,
        signal: SignalType
    ) -> bool:
        """
        Check if position should be exited based on stops.
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
            high: Period high price
            low: Period low price
            signal: Current position direction
            
        Returns:
            True if position should be exited
        """
        # Check stop-loss
        if symbol in self.stop_prices and self.stop_prices[symbol] is not None:
            stop = self.stop_prices[symbol]
            if signal == SignalType.LONG and low <= stop:
                return True
            elif signal == SignalType.SHORT and high >= stop:
                return True
        
        # Check take-profit
        if symbol in self.take_profit_prices and self.take_profit_prices[symbol] is not None:
            tp = self.take_profit_prices[symbol]
            if signal == SignalType.LONG and high >= tp:
                return True
            elif signal == SignalType.SHORT and low <= tp:
                return True
        
        return False
    
    def apply_filters(self, data: pd.DataFrame, signals: pd.Series) -> pd.Series:
        """
        Apply additional filters to trading signals (override in subclass).
        
        Examples:
        - Volume filters
        - Volatility filters
        - Market regime filters
        - Time-of-day filters
        
        Args:
            data: DataFrame with market data and indicators
            signals: Raw signals from generate_signals()
            
        Returns:
            Filtered signals
        """
        return signals
    
    def get_required_indicators(self) -> List[str]:
        """
        Return list of required indicators for this strategy.
        Override in subclass to specify indicators needed.
        
        Returns:
            List of indicator names
        """
        return []
    
    def validate_data(self, data: pd.DataFrame) -> bool:
        """
        Validate that data has required columns and indicators.
        
        Args:
            data: DataFrame to validate
            
        Returns:
            True if data is valid
        """
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        required_indicators = self.get_required_indicators()
        
        missing_cols = [col for col in required_cols if col not in data.columns]
        missing_indicators = [ind for ind in required_indicators if ind not in data.columns]
        
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        if missing_indicators:
            raise ValueError(f"Missing required indicators: {missing_indicators}")
            
        return True
    
    def get_parameters(self) -> Dict:
        """
        Get strategy parameters for logging/optimization.
        
        Returns:
            Dictionary of parameters
        """
        params = {
            'name': self.name,
            'position_sizing_method': self.position_sizing_method.value,
            'position_size_pct': self.position_size_pct,
            'max_position_size': self.max_position_size,
            'stop_loss_pct': self.stop_loss_pct,
            'take_profit_pct': self.take_profit_pct,
            'trailing_stop_pct': self.trailing_stop_pct,
            'max_positions': self.max_positions,
            'risk_per_trade': self.risk_per_trade,
            'use_atr_stops': self.use_atr_stops,
            'atr_stop_multiplier': self.atr_stop_multiplier,
        }
        params.update(self.parameters)
        return params
    
    def __repr__(self) -> str:
        return f"<AdvancedStrategy: {self.name}>"
