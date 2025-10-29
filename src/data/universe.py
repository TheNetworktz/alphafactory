"""
Universe Screener for AlphaFactory OS
Filters stocks based on STM strategy requirements

Filters:
- Price range ($10-$500)
- Volume (>500K/day average)
- Market cap (>$1B)
- Exclude penny stocks
- Focus on liquid, quality stocks
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime, timedelta


class UniverseScreener:
    """
    Screen stocks for STM strategy universe.
    
    Identifies liquid, quality stocks suitable for short-term mean reversion.
    """
    
    def __init__(
        self,
        min_price: float = 10.0,
        max_price: float = 500.0,
        min_avg_volume: int = 500000,
        min_market_cap: float = 1e9,  # $1 billion
        volume_lookback_days: int = 20,
        exclude_sectors: Optional[List[str]] = None,
        focus_indices: Optional[List[str]] = None
    ):
        """
        Initialize universe screener.
        
        Args:
            min_price: Minimum stock price
            max_price: Maximum stock price
            min_avg_volume: Minimum average daily volume
            min_market_cap: Minimum market capitalization
            volume_lookback_days: Days to calculate average volume
            exclude_sectors: Sectors to exclude (e.g., ['Utilities'])
            focus_indices: Indices to focus on (e.g., ['SP500', 'RUSSELL1000'])
        """
        self.min_price = min_price
        self.max_price = max_price
        self.min_avg_volume = min_avg_volume
        self.min_market_cap = min_market_cap
        self.volume_lookback_days = volume_lookback_days
        self.exclude_sectors = exclude_sectors or []
        self.focus_indices = focus_indices or ['SP500']
    
    def get_sp500_symbols(self) -> List[str]:
        """
        Get S&P 500 symbols.
        
        In production, this would query your database or use an API.
        For now, returns common large-cap symbols for testing.
        """
        # Top liquid S&P 500 stocks (subset for testing)
        return [
            # Tech
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'AVGO',
            # Finance
            'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'BLK', 'SCHW',
            # Healthcare
            'UNH', 'JNJ', 'LLY', 'PFE', 'ABBV', 'TMO', 'MRK', 'DHR',
            # Consumer
            'WMT', 'HD', 'PG', 'KO', 'PEP', 'COST', 'NKE', 'MCD',
            # Industrial
            'CAT', 'BA', 'UPS', 'HON', 'UNP', 'RTX', 'LMT', 'DE',
            # Energy
            'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'PXD',
            # Comm
            'VZ', 'T', 'TMUS', 'DIS', 'NFLX', 'CMCSA',
        ]
    
    def get_russell1000_symbols(self) -> List[str]:
        """Get Russell 1000 symbols (subset)."""
        # Would query from database in production
        return self.get_sp500_symbols()  # Simplified for now
    
    def get_universe_symbols(self) -> List[str]:
        """
        Get all symbols in the universe based on focus indices.
        
        Returns:
            List of stock symbols
        """
        symbols = set()
        
        if 'SP500' in self.focus_indices:
            symbols.update(self.get_sp500_symbols())
        
        if 'RUSSELL1000' in self.focus_indices:
            symbols.update(self.get_russell1000_symbols())
        
        return sorted(list(symbols))
    
    def passes_filters(
        self,
        symbol: str,
        price: float,
        avg_volume: float,
        market_cap: Optional[float] = None,
        sector: Optional[str] = None
    ) -> bool:
        """
        Check if a symbol passes all filters.
        
        Args:
            symbol: Stock symbol
            price: Current price
            avg_volume: Average daily volume
            market_cap: Market capitalization
            sector: Stock sector
            
        Returns:
            True if passes all filters
        """
        # Price range
        if price < self.min_price or price > self.max_price:
            return False
        
        # Volume
        if avg_volume < self.min_avg_volume:
            return False
        
        # Market cap
        if market_cap is not None and market_cap < self.min_market_cap:
            return False
        
        # Sector exclusions
        if sector and sector in self.exclude_sectors:
            return False
        
        return True
    
    def screen_universe(
        self,
        db_manager,
        as_of_date: Optional[datetime] = None
    ) -> List[str]:
        """
        Screen universe and return qualified symbols.
        
        Args:
            db_manager: Database manager instance
            as_of_date: Date to screen as of (None = most recent)
            
        Returns:
            List of qualified symbols
        """
        if as_of_date is None:
            as_of_date = datetime.now()
        
        universe = self.get_universe_symbols()
        qualified = []
        
        for symbol in universe:
            try:
                # Get recent data
                data = db_manager.get_daily_bars(
                    symbol,
                    start_date=as_of_date - timedelta(days=self.volume_lookback_days + 10),
                    end_date=as_of_date
                )
                
                if data.empty or len(data) < self.volume_lookback_days:
                    continue
                
                # Calculate metrics
                recent_price = data['close'].iloc[-1]
                avg_volume = data['volume'].tail(self.volume_lookback_days).mean()
                
                # Get market cap (if available in database)
                market_cap = None
                try:
                    symbol_info = db_manager.get_symbol_info(symbol)
                    if symbol_info:
                        market_cap = symbol_info.get('market_cap')
                except:
                    pass
                
                # Check filters
                if self.passes_filters(symbol, recent_price, avg_volume, market_cap):
                    qualified.append(symbol)
            
            except Exception as e:
                print(f"Error screening {symbol}: {e}")
                continue
        
        return qualified
    
    def get_universe_stats(self, qualified_symbols: List[str], db_manager) -> pd.DataFrame:
        """
        Get statistics for qualified universe.
        
        Args:
            qualified_symbols: List of qualified symbols
            db_manager: Database manager instance
            
        Returns:
            DataFrame with symbol statistics
        """
        stats = []
        
        for symbol in qualified_symbols:
            try:
                data = db_manager.get_daily_bars(symbol, days=30)
                if data.empty:
                    continue
                
                stats.append({
                    'symbol': symbol,
                    'price': data['close'].iloc[-1],
                    'avg_volume': data['volume'].mean(),
                    'volatility': data['close'].pct_change().std() * np.sqrt(252) * 100,
                    'return_1m': ((data['close'].iloc[-1] / data['close'].iloc[0]) - 1) * 100
                })
            except:
                continue
        
        return pd.DataFrame(stats).sort_values('avg_volume', ascending=False)


# Preset universe configurations
class SP500_Universe(UniverseScreener):
    """S&P 500 focus universe."""
    def __init__(self):
        super().__init__(
            min_price=10.0,
            max_price=500.0,
            min_avg_volume=500000,
            min_market_cap=1e9,
            focus_indices=['SP500']
        )


class LargeCap_Universe(UniverseScreener):
    """Large cap focus (more conservative)."""
    def __init__(self):
        super().__init__(
            min_price=20.0,
            max_price=500.0,
            min_avg_volume=1000000,
            min_market_cap=10e9,  # $10B+
            focus_indices=['SP500']
        )


class HighVolume_Universe(UniverseScreener):
    """High volume stocks for scalping."""
    def __init__(self):
        super().__init__(
            min_price=10.0,
            max_price=300.0,
            min_avg_volume=2000000,  # 2M+ shares/day
            min_market_cap=5e9,
            focus_indices=['SP500']
        )


# Example usage
def example_screen_universe():
    """
    Example of using the universe screener.
    
    In production, integrate with your DatabaseManager.
    """
    from src.database.db_manager import DatabaseManager
    
    # Initialize screener
    screener = SP500_Universe()
    
    # Get universe symbols
    universe = screener.get_universe_symbols()
    print(f"Total universe: {len(universe)} symbols")
    
    # Screen with database
    db = DatabaseManager()
    qualified = screener.screen_universe(db)
    print(f"Qualified: {len(qualified)} symbols")
    print(f"Symbols: {', '.join(qualified[:20])}...")  # First 20
    
    # Get stats
    stats = screener.get_universe_stats(qualified, db)
    print("\nTop 10 by volume:")
    print(stats.head(10))
    
    return qualified


if __name__ == "__main__":
    # Example usage
    print("Universe Screener Example")
    print("="*60)
    
    # Create screener
    screener = SP500_Universe()
    
    # Get symbols (without database)
    symbols = screener.get_universe_symbols()
    print(f"\nS&P 500 Universe: {len(symbols)} symbols")
    print(f"Sample: {', '.join(symbols[:10])}...")
    
    # Example filters
    example_price = 150.0
    example_volume = 2000000
    example_mcap = 50e9
    
    passes = screener.passes_filters(
        symbol="AAPL",
        price=example_price,
        avg_volume=example_volume,
        market_cap=example_mcap
    )
    
    print(f"\nExample filter test:")
    print(f"  Price: ${example_price}, Volume: {example_volume:,}, MCap: ${example_mcap/1e9:.1f}B")
    print(f"  Passes: {passes}")
