"""
AlphaFactory OS - First Backtest
Run a simple SMA crossover strategy backtest
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from datetime import datetime, timedelta
from loguru import logger

from src.database.db_manager import db_manager
from src.data.data_downloader import DataDownloader
from src.indicators.indicator_calculator import IndicatorCalculator
from src.strategies.sma_crossover import SMACrossoverStrategy
from src.backtest.backtest_engine import BacktestEngine


def main():
    """Run first backtest"""
    
    logger.info("="*60)
    logger.info("ALPHAFACTORY OS - FIRST BACKTEST")
    logger.info("="*60)
    
    # Initialize
    db_manager.initialize()
    downloader = DataDownloader()
    calc = IndicatorCalculator()
    
    # Step 1: Download more data (need at least 50+ days for SMA 50)
    symbol = 'AAPL'
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')  # 1 year
    
    logger.info(f"\n📥 Step 1: Downloading {symbol} data...")
    logger.info(f"Period: {start_date} to {end_date}")
    
    success = downloader.download_and_save(symbol, start_date, end_date)
    
    if not success:
        logger.error("Failed to download data")
        return
    
    # Step 2: Load data with indicators
    logger.info(f"\n📊 Step 2: Loading data and calculating indicators...")
    
    df = calc.load_data_with_indicators(symbol, start_date, end_date)
    
    if df is None or len(df) < 50:
        logger.error(f"Insufficient data: {len(df) if df is not None else 0} bars")
        return
    
    logger.success(f"✓ Loaded {len(df)} bars with indicators")
    
    # Step 3: Create strategy and generate signals
    logger.info(f"\n🎯 Step 3: Generating strategy signals...")
    
    strategy = SMACrossoverStrategy(fast_period=20, slow_period=50)
    df = strategy.generate_signals(df)
    
    entries = df['entry'].sum()
    exits = df['exit'].sum()
    logger.info(f"Generated {entries} entry signals and {exits} exit signals")
    
    # Step 4: Run backtest
    logger.info(f"\n🚀 Step 4: Running backtest...")
    
    engine = BacktestEngine(
        initial_capital=100000,
        commission_pct=0.001,
        slippage_pct=0.0005
    )
    
    results = engine.run(df, position_size=0.95)  # Use 95% of capital
    
    # Step 5: Display results
    logger.info(f"\n📈 Step 5: Backtest Complete!")
    
    engine.print_results(results)
    
    # Show some trades
    if results['trades']:
        logger.info(f"\n💼 First 5 trades:")
        for i, trade in enumerate(results['trades'][:5], 1):
            logger.info(f"Trade {i}: Entry={trade['entry_date'].strftime('%Y-%m-%d')} @ ${trade['entry_price']:.2f}, "
                       f"Exit={trade['exit_date'].strftime('%Y-%m-%d')} @ ${trade['exit_price']:.2f}, "
                       f"P&L=${trade['pnl']:.2f} ({trade['return_pct']:.2f}%)")
    
    logger.success("\n✓ YOUR FIRST BACKTEST IS COMPLETE! 🎉\n")
    
    # Save results
    results_dir = project_root / 'results'
    results_dir.mkdir(exist_ok=True)
    
    csv_path = results_dir / f'backtest_{symbol}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    results['df'].to_csv(csv_path)
    logger.info(f"Results saved to: {csv_path}")


if __name__ == '__main__':
    main()