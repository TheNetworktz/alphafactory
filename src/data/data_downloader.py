"""
AlphaFactory OS - Data Downloader
Fetches market data from Polygon.io, Alpha Vantage, and Yahoo Finance
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime, timedelta
from typing import List, Optional
import pandas as pd
from loguru import logger

from src.config.config_loader import config
from src.database.db_manager import db_manager
from src.database.models import Symbol, DailyBar


class DataDownloader:
    """
    Downloads and stores market data from multiple sources
    """
    
    def __init__(self):
        """Initialize data downloader"""
        self.polygon_key = config.polygon_api_key
        self.alpha_vantage_key = config.alpha_vantage_api_key
        
        # Check which data sources are available
        self.has_polygon = bool(self.polygon_key)
        self.has_alpha_vantage = bool(self.alpha_vantage_key)
        
        if self.has_polygon:
            logger.info("✓ Polygon.io API configured")
        if self.has_alpha_vantage:
            logger.info("✓ Alpha Vantage API configured")
        
        if not self.has_polygon and not self.has_alpha_vantage:
            logger.warning("⚠ No premium data sources configured - using Yahoo Finance only")
    
    def download_daily_bars(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        source: str = 'auto'
    ) -> Optional[pd.DataFrame]:
        """
        Download daily OHLCV data for a symbol
        
        Args:
            symbol: Stock ticker (e.g., 'AAPL')
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            source: Data source ('auto', 'polygon', 'yfinance', 'alpha_vantage')
        
        Returns:
            DataFrame with OHLCV data or None if failed
        """
        logger.info(f"Downloading {symbol} from {start_date} to {end_date} (source: {source})")
        
        # Auto-select best available source
        if source == 'auto':
            if self.has_polygon:
                source = 'polygon'
            elif self.has_alpha_vantage:
                source = 'alpha_vantage'
            else:
                source = 'yfinance'
        
        # Download from selected source
        try:
            if source == 'polygon':
                df = self._download_from_polygon(symbol, start_date, end_date)
            elif source == 'alpha_vantage':
                df = self._download_from_alpha_vantage(symbol, start_date, end_date)
            elif source == 'yfinance':
                df = self._download_from_yfinance(symbol, start_date, end_date)
            else:
                logger.error(f"Unknown data source: {source}")
                return None
            
            if df is not None and not df.empty:
                logger.success(f"✓ Downloaded {len(df)} bars for {symbol}")
                return df
            else:
                logger.warning(f"No data returned for {symbol}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to download {symbol}: {e}")
            return None
    
    def _download_from_polygon(
        self,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """Download from Polygon.io"""
        try:
            from polygon import RESTClient
            
            client = RESTClient(api_key=self.polygon_key)
            
            # Convert dates to Polygon format
            start = datetime.strptime(start_date, '%Y-%m-%d').strftime('%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d').strftime('%Y-%m-%d')
            
            # Fetch aggregates (daily bars)
            aggs = client.get_aggs(
                ticker=symbol,
                multiplier=1,
                timespan='day',
                from_=start,
                to=end,
                adjusted=True,
                limit=50000
            )
            
            if not aggs:
                return None
            
            # Convert to DataFrame
            data = []
            for agg in aggs:
                data.append({
                    'date': datetime.fromtimestamp(agg.timestamp / 1000),
                    'open': agg.open,
                    'high': agg.high,
                    'low': agg.low,
                    'close': agg.close,
                    'volume': agg.volume,
                    'adj_close': agg.close  # Already adjusted
                })
            
            df = pd.DataFrame(data)
            df.set_index('date', inplace=True)
            return df
            
        except Exception as e:
            logger.error(f"Polygon download failed: {e}")
            return None
    
    def _download_from_alpha_vantage(
        self,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """Download from Alpha Vantage"""
        try:
            import requests
            
            url = 'https://www.alphavantage.co/query'
            params = {
                'function': 'TIME_SERIES_DAILY_ADJUSTED',
                'symbol': symbol,
                'outputsize': 'full',
                'apikey': self.alpha_vantage_key
            }
            
            response = requests.get(url, params=params, timeout=30)
            data = response.json()
            
            if 'Time Series (Daily)' not in data:
                logger.warning(f"Alpha Vantage: No data for {symbol}")
                return None
            
            # Parse response
            time_series = data['Time Series (Daily)']
            rows = []
            
            for date_str, values in time_series.items():
                date = datetime.strptime(date_str, '%Y-%m-%d')
                
                # Filter by date range
                if start_date <= date_str <= end_date:
                    rows.append({
                        'date': date,
                        'open': float(values['1. open']),
                        'high': float(values['2. high']),
                        'low': float(values['3. low']),
                        'close': float(values['4. close']),
                        'adj_close': float(values['5. adjusted close']),
                        'volume': float(values['6. volume'])
                    })
            
            if not rows:
                return None
            
            df = pd.DataFrame(rows)
            df.set_index('date', inplace=True)
            df.sort_index(inplace=True)
            return df
            
        except Exception as e:
            logger.error(f"Alpha Vantage download failed: {e}")
            return None
    
    def _download_from_yfinance(
        self,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """Download from Yahoo Finance"""
        try:
            import yfinance as yf
            
            # Download data
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date)
            
            if df.empty:
                return None
            
            # Standardize column names
            df = df.rename(columns={
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })
            
            # Add adj_close (yfinance Close is already adjusted)
            df['adj_close'] = df['close']
            
            # Select relevant columns
            df = df[['open', 'high', 'low', 'close', 'volume', 'adj_close']]
            
            return df
            
        except Exception as e:
            logger.error(f"Yahoo Finance download failed: {e}")
            return None
    
    def save_to_database(
        self,
        symbol: str,
        df: pd.DataFrame
    ) -> bool:
        """
        Save downloaded data to database
        
        Args:
            symbol: Stock ticker
            df: DataFrame with OHLCV data
        
        Returns:
            True if successful, False otherwise
        """
        try:
            with db_manager.get_session() as session:
                # Get or create symbol
                symbol_obj = session.query(Symbol).filter_by(symbol=symbol).first()
                if not symbol_obj:
                    symbol_obj = Symbol(symbol=symbol, name=symbol)
                    session.add(symbol_obj)
                    session.flush()
                
                # Add daily bars
                bars_added = 0
                for date, row in df.iterrows():
                    # Check if bar already exists
                    existing = session.query(DailyBar).filter_by(
                        symbol_id=symbol_obj.id,
                        date=date
                    ).first()
                    
                    if existing:
                        # Update existing bar
                        existing.open = row['open']
                        existing.high = row['high']
                        existing.low = row['low']
                        existing.close = row['close']
                        existing.volume = row['volume']
                        existing.adj_close = row.get('adj_close', row['close'])
                    else:
                        # Create new bar
                        bar = DailyBar(
                            symbol_id=symbol_obj.id,
                            date=date,
                            open=row['open'],
                            high=row['high'],
                            low=row['low'],
                            close=row['close'],
                            volume=row['volume'],
                            adj_close=row.get('adj_close', row['close'])
                        )
                        session.add(bar)
                        bars_added += 1
                
                session.commit()
                logger.success(f"✓ Saved {bars_added} new bars for {symbol} to database")
                return True
                
        except Exception as e:
            logger.error(f"Failed to save {symbol} to database: {e}")
            return False
    
    def download_and_save(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        source: str = 'auto'
    ) -> bool:
        """
        Download data and save to database in one step
        
        Args:
            symbol: Stock ticker
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            source: Data source ('auto', 'polygon', 'yfinance', 'alpha_vantage')
        
        Returns:
            True if successful, False otherwise
        """
        # Download data
        df = self.download_daily_bars(symbol, start_date, end_date, source)
        
        if df is None or df.empty:
            return False
        
        # Save to database
        return self.save_to_database(symbol, df)


if __name__ == '__main__':
    """Test data downloader"""
    from loguru import logger
    
    logger.info("Testing data downloader...")
    
    # Initialize database
    db_manager.initialize()
    
    # Create downloader
    downloader = DataDownloader()
    
    # Test download (last 30 days of AAPL)
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    logger.info(f"Downloading AAPL from {start_date} to {end_date}")
    
    success = downloader.download_and_save('AAPL', start_date, end_date)
    
    if success:
        logger.success("✓ Data downloader test complete!")
    else:
        logger.error("✗ Data downloader test failed!")