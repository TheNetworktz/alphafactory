"""
AlphaFactory OS - Simple Moving Average Crossover Strategy
Classic trend-following strategy: Buy when fast SMA crosses above slow SMA
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from loguru import logger
from typing import Dict, Optional


class SMACrossoverStrategy:
    """
    Simple Moving Average Crossover Strategy
    
    Rules:
    - BUY: When fast SMA crosses above slow SMA (golden cross)
    - SELL: When fast SMA crosses below slow SMA (death cross)
    
    Parameters:
    - fast_period: Fast SMA period (default: 20)
    - slow_period: Slow SMA period (default: 50)
    """
    
    def __init__(self, fast_period: int = 20, slow_period: int = 50):
        """
        Initialize strategy
        
        Args:
            fast_period: Fast SMA period
            slow_period: Slow SMA period
        """
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.name = f"SMA_Crossover_{fast_period}_{slow_period}"
        
        logger.info(f"Initialized {self.name}")
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals
        
        Args:
            df: DataFrame with OHLCV data and indicators
        
        Returns:
            DataFrame with signals added
        """
        df = df.copy()
        
        # Get or calculate SMAs
        if f'sma_{self.fast_period}' not in df.columns:
            df[f'sma_{self.fast_period}'] = df['close'].rolling(window=self.fast_period).mean()
        
        if f'sma_{self.slow_period}' not in df.columns:
            df[f'sma_{self.slow_period}'] = df['close'].rolling(window=self.slow_period).mean()
        
        fast_sma = df[f'sma_{self.fast_period}']
        slow_sma = df[f'sma_{self.slow_period}']
        
        # Initialize signal column
        df['signal'] = 0  # 0 = no position, 1 = long, -1 = short
        
        # Generate crossover signals
        # 1 when fast > slow (bullish), -1 when fast < slow (bearish)
        df.loc[fast_sma > slow_sma, 'signal'] = 1
        df.loc[fast_sma < slow_sma, 'signal'] = -1
        
        # Generate position changes (entries and exits)
        df['position'] = df['signal'].diff()
        
        # Mark entry and exit points
        df['entry'] = 0
        df['exit'] = 0
        
        # Entry: signal changes from 0 or -1 to 1 (buy signal)
        df.loc[df['position'] > 0, 'entry'] = 1
        
        # Exit: signal changes from 1 to 0 or -1 (sell signal)
        df.loc[df['position'] < 0, 'exit'] = 1
        
        return df
    
    def get_parameters(self) -> Dict:
        """Get strategy parameters"""
        return {
            'name': self.name,
            'fast_period': self.fast_period,
            'slow_period': self.slow_period
        }


if __name__ == '__main__':
    """Test strategy signal generation"""
    from loguru import logger
    from datetime import datetime, timedelta
    from src.indicators.indicator_calculator import IndicatorCalculator
    from src.database.db_manager import db_manager
    
    logger.info("Testing SMA Crossover Strategy...")
    
    # Initialize
    db_manager.initialize()
    calc = IndicatorCalculator()
    
    # Load data with indicators
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=100)).strftime('%Y-%m-%d')
    
    logger.info(f"Loading AAPL data from {start_date} to {end_date}")
    df = calc.load_data_with_indicators('AAPL', start_date, end_date)
    
    if df is not None and len(df) > 0:
        # Create strategy
        strategy = SMArossoverStrategy(fast_period=20, slow_period=50)
        
        # Generate signals
        df = strategy.generate_signals(df)
        
        # Show results
        logger.info(f"\nGenerated signals for {len(df)} bars")
        
        # Count signals
        entries = df['entry'].sum()
        exits = df['exit'].sum()
        logger.info(f"Entry signals: {entries}")
        logger.info(f"Exit signals: {exits}")
        
        # Show last few signals
        logger.info("\nLast 10 days with signals:")
        cols = ['close', f'sma_{strategy.fast_period}', f'sma_{strategy.slow_period}', 'signal', 'entry', 'exit']
        print(df[cols].tail(10))
        
        logger.success("✓ Strategy test complete!")
    else:
        logger.error("✗ No data available. Download more data first.")