"""
AlphaFactory OS - Backtest Engine
Vectorized backtesting engine for strategy evaluation
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from loguru import logger
from datetime import datetime
from typing import Dict, Optional, List

from src.config.config_loader import config


class BacktestEngine:
    """
    Vectorized backtest engine
    
    Fast backtesting using pandas vectorization
    Supports:
    - Long-only strategies
    - Commission and slippage
    - Position sizing
    - Performance metrics
    """
    
    def __init__(
        self,
        initial_capital: float = 100000,
        commission_pct: float = 0.001,  # 0.1% = $0.005/share * price
        slippage_pct: float = 0.0005    # 0.05%
    ):
        """
        Initialize backtest engine
        
        Args:
            initial_capital: Starting capital
            commission_pct: Commission as percentage of trade value
            slippage_pct: Slippage as percentage of price
        """
        self.initial_capital = initial_capital
        self.commission_pct = commission_pct
        self.slippage_pct = slippage_pct
        
        logger.info(f"Backtest engine initialized with ${initial_capital:,.0f}")
    
    def run(
        self,
        df: pd.DataFrame,
        position_size: float = 1.0
    ) -> Dict:
        """
        Run backtest
        
        Args:
            df: DataFrame with signals (must have 'signal' column)
            position_size: Position size as fraction of capital (0-1)
        
        Returns:
            Dictionary with backtest results
        """
        logger.info(f"Running backtest on {len(df)} bars...")
        
        df = df.copy()
        
        # Initialize columns
        df['position'] = 0.0  # Position size (shares)
        df['cash'] = float(self.initial_capital)
        df['holdings'] = 0.0  # Value of holdings
        df['equity'] = float(self.initial_capital)  # Total equity
        df['returns'] = 0.0  # Daily returns
        df['trade'] = 0  # Trade indicator
        
        # Track trades
        trades = []
        current_position = 0
        entry_price = 0
        entry_date = None
        
        # Iterate through bars
        for i in range(1, len(df)):
            prev_idx = df.index[i-1]
            curr_idx = df.index[i]
            
            prev_signal = df.loc[prev_idx, 'signal']
            curr_signal = df.loc[curr_idx, 'signal']
            
            price = df.loc[curr_idx, 'close']
            prev_cash = df.loc[prev_idx, 'cash']
            prev_position = df.loc[prev_idx, 'position']
            
            # Check for signal change (trade)
            if prev_signal != curr_signal:
                # Close existing position
                if prev_position > 0:
                    # Sell
                    sell_price = price * (1 - self.slippage_pct)
                    proceeds = prev_position * sell_price
                    commission = proceeds * self.commission_pct
                    cash_change = proceeds - commission
                    
                    # Record trade
                    pnl = (sell_price - entry_price) * prev_position - commission
                    trades.append({
                        'entry_date': entry_date,
                        'exit_date': curr_idx,
                        'entry_price': entry_price,
                        'exit_price': sell_price,
                        'shares': prev_position,
                        'pnl': pnl,
                        'return_pct': ((sell_price - entry_price) / entry_price) * 100
                    })
                    
                    current_position = 0
                    df.loc[curr_idx, 'cash'] = prev_cash + cash_change
                    df.loc[curr_idx, 'position'] = 0
                    df.loc[curr_idx, 'trade'] = -1  # Sell
                
                # Open new position
                if curr_signal > 0:
                    # Buy
                    buy_price = price * (1 + self.slippage_pct)
                    available_cash = df.loc[curr_idx, 'cash'] if df.loc[curr_idx, 'cash'] > 0 else prev_cash
                    position_value = available_cash * position_size
                    shares = position_value / buy_price
                    cost = shares * buy_price
                    commission = cost * self.commission_pct
                    
                    current_position = shares
                    entry_price = buy_price
                    entry_date = curr_idx
                    
                    df.loc[curr_idx, 'cash'] = available_cash - cost - commission
                    df.loc[curr_idx, 'position'] = shares
                    df.loc[curr_idx, 'trade'] = 1  # Buy
                else:
                    # No position
                    df.loc[curr_idx, 'cash'] = df.loc[curr_idx, 'cash'] if df.loc[curr_idx, 'cash'] > 0 else prev_cash
                    df.loc[curr_idx, 'position'] = 0
            else:
                # No trade - carry forward
                df.loc[curr_idx, 'cash'] = prev_cash
                df.loc[curr_idx, 'position'] = prev_position
            
            # Calculate equity
            df.loc[curr_idx, 'holdings'] = df.loc[curr_idx, 'position'] * price
            df.loc[curr_idx, 'equity'] = df.loc[curr_idx, 'cash'] + df.loc[curr_idx, 'holdings']
            
            # Calculate returns
            prev_equity = df.loc[prev_idx, 'equity']
            df.loc[curr_idx, 'returns'] = (df.loc[curr_idx, 'equity'] - prev_equity) / prev_equity
        
        # Calculate performance metrics
        results = self._calculate_metrics(df, trades)
        
        # Add DataFrame to results
        results['df'] = df
        results['trades'] = trades
        
        return results
    
    def _calculate_metrics(self, df: pd.DataFrame, trades: List[Dict]) -> Dict:
        """Calculate performance metrics"""
        
        final_equity = df['equity'].iloc[-1]
        total_return = (final_equity - self.initial_capital) / self.initial_capital
        
        # Time period
        days = (df.index[-1] - df.index[0]).days
        years = days / 365.25
        
        # Annualized return
        annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
        
        # Volatility (annualized)
        daily_returns = df['returns'].dropna()
        volatility = daily_returns.std() * np.sqrt(252)
        
        # Sharpe ratio (assuming 0% risk-free rate)
        sharpe_ratio = (annual_return / volatility) if volatility > 0 else 0
        
        # Maximum drawdown
        cumulative = (1 + df['returns']).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # Trade statistics
        num_trades = len(trades)
        if num_trades > 0:
            winning_trades = [t for t in trades if t['pnl'] > 0]
            losing_trades = [t for t in trades if t['pnl'] <= 0]
            
            win_rate = len(winning_trades) / num_trades
            avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
            avg_loss = np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0
            profit_factor = abs(sum([t['pnl'] for t in winning_trades]) / sum([t['pnl'] for t in losing_trades])) if losing_trades and sum([t['pnl'] for t in losing_trades]) != 0 else 0
        else:
            win_rate = 0
            avg_win = 0
            avg_loss = 0
            profit_factor = 0
        
        # Sortino ratio (downside deviation)
        downside_returns = daily_returns[daily_returns < 0]
        downside_std = downside_returns.std() * np.sqrt(252)
        sortino_ratio = (annual_return / downside_std) if downside_std > 0 else 0
        
        # Calmar ratio (return / max drawdown)
        calmar_ratio = (annual_return / abs(max_drawdown)) if max_drawdown < 0 else 0
        
        results = {
            'initial_capital': self.initial_capital,
            'final_equity': final_equity,
            'total_return': total_return * 100,  # percentage
            'annual_return': annual_return * 100,  # percentage
            'volatility': volatility * 100,  # percentage
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'max_drawdown': max_drawdown * 100,  # percentage
            'calmar_ratio': calmar_ratio,
            'num_trades': num_trades,
            'win_rate': win_rate * 100,  # percentage
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'days': days,
            'years': years
        }
        
        return results
    
    def print_results(self, results: Dict) -> None:
        """Print backtest results in a formatted way"""
        
        print("\n" + "="*60)
        print("BACKTEST RESULTS")
        print("="*60)
        
        print(f"\n📊 PORTFOLIO PERFORMANCE")
        print(f"Initial Capital:    ${results['initial_capital']:>15,.2f}")
        print(f"Final Equity:       ${results['final_equity']:>15,.2f}")
        print(f"Total Return:       {results['total_return']:>15.2f}%")
        print(f"Annual Return:      {results['annual_return']:>15.2f}%")
        print(f"Volatility (Ann.):  {results['volatility']:>15.2f}%")
        
        print(f"\n📈 RISK METRICS")
        print(f"Sharpe Ratio:       {results['sharpe_ratio']:>15.2f}")
        print(f"Sortino Ratio:      {results['sortino_ratio']:>15.2f}")
        print(f"Calmar Ratio:       {results['calmar_ratio']:>15.2f}")
        print(f"Max Drawdown:       {results['max_drawdown']:>15.2f}%")
        
        print(f"\n💼 TRADING STATISTICS")
        print(f"Number of Trades:   {results['num_trades']:>15}")
        print(f"Win Rate:           {results['win_rate']:>15.2f}%")
        print(f"Avg Win:            ${results['avg_win']:>15,.2f}")
        print(f"Avg Loss:           ${results['avg_loss']:>15,.2f}")
        print(f"Profit Factor:      {results['profit_factor']:>15.2f}")
        
        print(f"\n⏱️  BACKTEST PERIOD")
        print(f"Days:               {results['days']:>15}")
        print(f"Years:              {results['years']:>15.2f}")
        
        print("\n" + "="*60 + "\n")


if __name__ == '__main__':
    """Test backtest engine"""
    logger.info("Backtest engine ready for use")
    logger.info("Import and use with strategy signals")