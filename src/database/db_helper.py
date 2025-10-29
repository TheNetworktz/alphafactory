"""
Database Helper Functions for AlphaFactory OS
Provides convenient data loading functions

This bridges the gap between DatabaseManager and your strategies.
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy import select

from src.database.models import DailyBar, Symbol
from src.database.db_manager import DatabaseManager


def get_daily_bars(symbol: str, days: int = 252, end_date: Optional[datetime] = None) -> pd.DataFrame:
    """
    Get daily bars for a symbol.
    
    Args:
        symbol: Stock symbol (e.g., 'AAPL')
        days: Number of days to retrieve (default: 252 = ~1 year)
        end_date: End date (default: None = most recent)
    
    Returns:
        pandas DataFrame with OHLCV data, indexed by date
    """
    db = DatabaseManager()
    
    # get_session() returns a generator, so we use 'with' or 'next'
    with db.get_session() as session:
        try:
            # Build query
            stmt = (select(DailyBar)
                    .join(Symbol)
                    .where(Symbol.symbol == symbol)
                    .order_by(DailyBar.date.desc())
                    .limit(days))
            
            if end_date:
                stmt = stmt.where(DailyBar.date <= end_date)
            
            # Execute query
            results = session.execute(stmt).scalars().all()
            
            # Convert to DataFrame
            if not results:
                return pd.DataFrame()
            
            data = [{
                'open': bar.open,
                'high': bar.high,
                'low': bar.low,
                'close': bar.close,
                'volume': bar.volume,
                'date': bar.date
            } for bar in results]
            
            df = pd.DataFrame(data)
            df.set_index('date', inplace=True)
            df.sort_index(inplace=True)  # Sort oldest to newest
            
            return df
        
        except Exception as e:
            print(f"Error loading data for {symbol}: {e}")
            return pd.DataFrame()


def get_daily_bars_with_indicators(symbol: str, days: int = 252) -> pd.DataFrame:
    """
    Get daily bars with indicators already calculated.
    
    Args:
        symbol: Stock symbol
        days: Number of days
    
    Returns:
        DataFrame with OHLCV + all indicators
    """
    from src.indicators.indicator_calculator import IndicatorCalculator
    
    # Get raw data
    df = get_daily_bars(symbol, days)
    
    if df.empty:
        return df
    
    # Calculate indicators
    calc = IndicatorCalculator()
    df = calc.calculate_all_indicators(df, save_to_db=False)
    
    return df


def get_multiple_symbols(symbols: list, days: int = 252) -> dict:
    """
    Get data for multiple symbols.
    
    Args:
        symbols: List of symbols
        days: Number of days
    
    Returns:
        Dictionary mapping symbol -> DataFrame
    """
    data_dict = {}
    
    for symbol in symbols:
        df = get_daily_bars_with_indicators(symbol, days)
        if not df.empty:
            data_dict[symbol] = df
    
    return data_dict


def get_symbol_info(symbol: str) -> Optional[dict]:
    """
    Get symbol information.
    
    Args:
        symbol: Stock symbol
    
    Returns:
        Dictionary with symbol info or None
    """
    db = DatabaseManager()
    
    with db.get_session() as session:
        try:
            stmt = select(Symbol).where(Symbol.symbol == symbol)
            result = session.execute(stmt).scalar_one_or_none()
            
            if result:
                return {
                    'symbol': result.symbol,
                    'name': result.name,
                    'exchange': result.exchange,
                    'sector': result.sector,
                    'industry': result.industry,
                    'market_cap': result.market_cap,
                }
            return None
        
        except Exception as e:
            print(f"Error getting symbol info: {e}")
            return None


if __name__ == "__main__":
    # Test the helper functions
    print("\n" + "="*70)
    print("TESTING DB_HELPER FUNCTIONS")
    print("="*70)
    
    # Test 1: Get daily bars
    print("\nTest 1: Get daily bars for AAPL")
    print("-"*70)
    df = get_daily_bars("AAPL", days=10)
    if not df.empty:
        print(f"✓ Loaded {len(df)} bars")
        print(f"  Columns: {list(df.columns)}")
        print(f"  Date range: {df.index[0].date()} to {df.index[-1].date()}")
        print("\nSample data:")
        print(df.head(3))
    else:
        print("✗ No data found")
    
    # Test 2: Get with indicators
    print("\n\nTest 2: Get daily bars WITH indicators")
    print("-"*70)
    df = get_daily_bars_with_indicators("AAPL", days=50)
    if not df.empty:
        print(f"✓ Loaded {len(df)} bars with indicators")
        print(f"  Total columns: {len(df.columns)}")
        print(f"  Indicator columns: {[col for col in df.columns if col not in ['open', 'high', 'low', 'close', 'volume']][:10]}")
    else:
        print("✗ No data found")
    
    # Test 3: Get symbol info
    print("\n\nTest 3: Get symbol info")
    print("-"*70)
    info = get_symbol_info("AAPL")
    if info:
        print("✓ Symbol info:")
        for key, value in info.items():
            print(f"  {key}: {value}")
    else:
        print("✗ Symbol not found")
    
    print("\n" + "="*70)
    print("✓ All tests complete!")
    print("="*70)
    print()
