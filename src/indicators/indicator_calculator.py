"""
AlphaFactory OS - Indicator Calculator
TA-Lib wrapper for calculating technical indicators with database caching
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
import talib
from loguru import logger
from typing import Dict, List, Optional

from src.config.config_loader import config
from src.database.db_manager import db_manager
from src.database.models import DailyBar


class IndicatorCalculator:
    """
    Calculate technical indicators using TA-Lib
    Caches results in database for performance
    """
    
    def __init__(self):
        """Initialize indicator calculator"""
        logger.info("Indicator calculator initialized")
    
    def calculate_all_indicators(
        self,
        df: pd.DataFrame,
        save_to_db: bool = False,
        symbol_id: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Calculate all common technical indicators
        
        Args:
            df: DataFrame with OHLCV data (must have: open, high, low, close, volume)
            save_to_db: Whether to save indicators to database
            symbol_id: Symbol ID for database saving
        
        Returns:
            DataFrame with indicators added
        """
        logger.info(f"Calculating indicators for {len(df)} bars")
        
        # Make a copy to avoid modifying original
        df = df.copy()
        
        # Extract price arrays
        open_prices = df['open'].values
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        volume = df['volume'].values
        
        # ====================================================================
        # MOVING AVERAGES
        # ====================================================================
        df['sma_20'] = talib.SMA(close, timeperiod=20)
        df['sma_50'] = talib.SMA(close, timeperiod=50)
        df['sma_200'] = talib.SMA(close, timeperiod=200)
        df['ema_12'] = talib.EMA(close, timeperiod=12)
        df['ema_26'] = talib.EMA(close, timeperiod=26)
        
        # ====================================================================
        # MOMENTUM INDICATORS
        # ====================================================================
        df['rsi_14'] = talib.RSI(close, timeperiod=14)
        df['rsi_7'] = talib.RSI(close, timeperiod=7)
        
        # MACD (Moving Average Convergence Divergence)
        macd, macd_signal, macd_hist = talib.MACD(
            close,
            fastperiod=12,
            slowperiod=26,
            signalperiod=9
        )
        df['macd'] = macd
        df['macd_signal'] = macd_signal
        df['macd_hist'] = macd_hist
        
        # Stochastic
        slowk, slowd = talib.STOCH(
            high, low, close,
            fastk_period=14,
            slowk_period=3,
            slowk_matype=0,
            slowd_period=3,
            slowd_matype=0
        )
        df['stoch_k'] = slowk
        df['stoch_d'] = slowd
        
        # Williams %R
        df['williams_r'] = talib.WILLR(high, low, close, timeperiod=14)
        
        # Rate of Change
        df['roc'] = talib.ROC(close, timeperiod=10)
        
        # ====================================================================
        # VOLATILITY INDICATORS
        # ====================================================================
        # Bollinger Bands
        upper, middle, lower = talib.BBANDS(
            close,
            timeperiod=20,
            nbdevup=2,
            nbdevdn=2,
            matype=0
        )
        df['bb_upper'] = upper
        df['bb_middle'] = middle
        df['bb_lower'] = lower
        df['bb_width'] = (upper - lower) / middle
        
        # Average True Range (ATR)
        df['atr_14'] = talib.ATR(high, low, close, timeperiod=14)
        
        # Standard Deviation
        df['std_20'] = talib.STDDEV(close, timeperiod=20)
        
        # ====================================================================
        # VOLUME INDICATORS
        # ====================================================================
        # On-Balance Volume
        df['obv'] = talib.OBV(close, volume)
        
        # Accumulation/Distribution
        df['ad'] = talib.AD(high, low, close, volume)
        
        # Chaikin A/D Oscillator
        df['adosc'] = talib.ADOSC(high, low, close, volume, fastperiod=3, slowperiod=10)
        
        # ====================================================================
        # TREND INDICATORS
        # ====================================================================
        # ADX (Average Directional Index)
        df['adx'] = talib.ADX(high, low, close, timeperiod=14)
        
        # Parabolic SAR
        df['sar'] = talib.SAR(high, low, acceleration=0.02, maximum=0.2)
        
        # ====================================================================
        # PATTERN RECOGNITION (Boolean signals)
        # ====================================================================
        df['cdl_doji'] = talib.CDLDOJI(open_prices, high, low, close)
        df['cdl_hammer'] = talib.CDLHAMMER(open_prices, high, low, close)
        df['cdl_engulfing'] = talib.CDLENGULFING(open_prices, high, low, close)
        df['cdl_morning_star'] = talib.CDLMORNINGSTAR(open_prices, high, low, close)
        df['cdl_evening_star'] = talib.CDLEVENINGSTAR(open_prices, high, low, close)
        
        # ====================================================================
        # DERIVED INDICATORS
        # ====================================================================
        # Price relative to moving averages
        df['price_to_sma20'] = close / df['sma_20']
        df['price_to_sma50'] = close / df['sma_50']
        df['price_to_sma200'] = close / df['sma_200']
        
        # Moving average crossovers (boolean)
        df['sma_20_above_50'] = df['sma_20'] > df['sma_50']
        df['sma_50_above_200'] = df['sma_50'] > df['sma_200']
        
        # Bollinger Band position (0-1, where is price in the band?)
        df['bb_position'] = (close - lower) / (upper - lower)
        
        # RSI overbought/oversold
        df['rsi_overbought'] = df['rsi_14'] > 70
        df['rsi_oversold'] = df['rsi_14'] < 30
        
        logger.success(f"✓ Calculated {len(df.columns) - 6} indicators")  # Subtract original OHLCV columns
        
        # Save to database if requested
        if save_to_db and symbol_id is not None:
            self._save_indicators_to_db(df, symbol_id)
        
        return df
    
    def _save_indicators_to_db(self, df: pd.DataFrame, symbol_id: int) -> None:
        """
        Save calculated indicators back to database
        
        Args:
            df: DataFrame with indicators
            symbol_id: Symbol ID
        """
        try:
            with db_manager.get_session() as session:
                updated = 0
                
                for date, row in df.iterrows():
                    # Find existing bar
                    bar = session.query(DailyBar).filter_by(
                        symbol_id=symbol_id,
                        date=date
                    ).first()
                    
                    if bar:
                        # Update indicators
                        bar.sma_20 = row.get('sma_20')
                        bar.sma_50 = row.get('sma_50')
                        bar.sma_200 = row.get('sma_200')
                        bar.rsi_14 = row.get('rsi_14')
                        bar.macd = row.get('macd')
                        bar.macd_signal = row.get('macd_signal')
                        bar.bbands_upper = row.get('bb_upper')
                        bar.bbands_middle = row.get('bb_middle')
                        bar.bbands_lower = row.get('bb_lower')
                        updated += 1
                
                session.commit()
                logger.success(f"✓ Saved indicators for {updated} bars to database")
                
        except Exception as e:
            logger.error(f"Failed to save indicators to database: {e}")
    
    def get_indicator_summary(self, df: pd.DataFrame) -> Dict:
        """
        Get summary statistics for indicators
        
        Args:
            df: DataFrame with indicators
        
        Returns:
            Dictionary with indicator summaries
        """
        summary = {}
        
        # Get last values (most recent)
        last_row = df.iloc[-1]
        
        summary['trend'] = {
            'sma_20': last_row.get('sma_20'),
            'sma_50': last_row.get('sma_50'),
            'sma_200': last_row.get('sma_200'),
            'price_to_sma20': last_row.get('price_to_sma20'),
            'adx': last_row.get('adx')
        }
        
        summary['momentum'] = {
            'rsi_14': last_row.get('rsi_14'),
            'macd': last_row.get('macd'),
            'macd_signal': last_row.get('macd_signal'),
            'roc': last_row.get('roc')
        }
        
        summary['volatility'] = {
            'bb_width': last_row.get('bb_width'),
            'atr_14': last_row.get('atr_14'),
            'std_20': last_row.get('std_20')
        }
        
        summary['signals'] = {
            'rsi_overbought': bool(last_row.get('rsi_overbought')),
            'rsi_oversold': bool(last_row.get('rsi_oversold')),
            'sma_20_above_50': bool(last_row.get('sma_20_above_50')),
            'sma_50_above_200': bool(last_row.get('sma_50_above_200'))
        }
        
        return summary
    
    def load_data_with_indicators(
        self,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """
        Load data from database and calculate indicators if needed
        
        Args:
            symbol: Stock ticker
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
        
        Returns:
            DataFrame with OHLCV and indicators
        """
        try:
            with db_manager.get_session() as session:
                # Get symbol
                from src.database.models import Symbol
                symbol_obj = session.query(Symbol).filter_by(symbol=symbol).first()
                
                if not symbol_obj:
                    logger.error(f"Symbol {symbol} not found in database")
                    return None
                
                # Get daily bars
                bars = session.query(DailyBar).filter(
                    DailyBar.symbol_id == symbol_obj.id,
                    DailyBar.date >= start_date,
                    DailyBar.date <= end_date
                ).order_by(DailyBar.date).all()
                
                if not bars:
                    logger.warning(f"No data found for {symbol} between {start_date} and {end_date}")
                    return None
                
                # Convert to DataFrame
                data = []
                for bar in bars:
                    data.append({
                        'date': bar.date,
                        'open': bar.open,
                        'high': bar.high,
                        'low': bar.low,
                        'close': bar.close,
                        'volume': bar.volume,
                        'adj_close': bar.adj_close
                    })
                
                df = pd.DataFrame(data)
                df.set_index('date', inplace=True)
                
                logger.info(f"Loaded {len(df)} bars for {symbol}")
                
                # Calculate indicators
                df = self.calculate_all_indicators(df, save_to_db=True, symbol_id=symbol_obj.id)
                
                return df
                
        except Exception as e:
            logger.error(f"Failed to load data with indicators: {e}")
            return None


if __name__ == '__main__':
    """Test indicator calculator"""
    from loguru import logger
    from datetime import datetime, timedelta
    
    logger.info("Testing indicator calculator...")
    
    # Initialize database
    db_manager.initialize()
    
    # Create calculator
    calc = IndicatorCalculator()
    
    # Load AAPL data (should exist from previous test)
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    df = calc.load_data_with_indicators('AAPL', start_date, end_date)
    
    if df is not None and not df.empty:
        logger.success(f"✓ Loaded {len(df)} bars with indicators")
        
        # Show summary
        summary = calc.get_indicator_summary(df)
        logger.info(f"Indicator summary: {summary}")
        
        # Show sample data
        logger.info("\nLast 5 days:")
        print(df[['close', 'sma_20', 'sma_50', 'rsi_14', 'macd']].tail())
        
        logger.success("✓ Indicator calculator test complete!")
    else:
        logger.error("✗ Failed to load data. Make sure AAPL data exists (run data_downloader.py first)")