"""
Portfolio Backtest Engine for AlphaFactory OS
Multi-symbol, concurrent position management

Handles:
- Multiple concurrent positions across different symbols
- Portfolio-level risk management
- Position sizing with capital constraints
- Stop-loss execution
- Maximum hold period enforcement
- Performance tracking at portfolio level
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import json


@dataclass
class Position:
    """Represents an open position."""
    symbol: str
    entry_date: datetime
    entry_price: float
    shares: int
    stop_price: float
    entry_value: float
    current_value: float = 0
    unrealized_pnl: float = 0
    
    def update(self, current_price: float):
        """Update position with current price."""
        self.current_value = current_price * self.shares
        self.unrealized_pnl = self.current_value - self.entry_value


@dataclass
class ClosedTrade:
    """Represents a closed trade."""
    symbol: str
    entry_date: datetime
    exit_date: datetime
    entry_price: float
    exit_price: float
    shares: int
    pnl: float
    pnl_pct: float
    exit_reason: str
    hold_days: int
    entry_value: float
    exit_value: float
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'symbol': self.symbol,
            'entry_date': str(self.entry_date),
            'exit_date': str(self.exit_date),
            'entry_price': round(self.entry_price, 2),
            'exit_price': round(self.exit_price, 2),
            'shares': self.shares,
            'pnl': round(self.pnl, 2),
            'pnl_pct': round(self.pnl_pct * 100, 2),
            'exit_reason': self.exit_reason,
            'hold_days': self.hold_days,
            'entry_value': round(self.entry_value, 2),
            'exit_value': round(self.exit_value, 2),
        }


class PortfolioBacktestEngine:
    """
    Portfolio-level backtesting engine for STM strategy.
    
    Manages multiple concurrent positions with proper capital allocation
    and risk management.
    """
    
    def __init__(
        self,
        initial_capital: float = 100000.0,
        commission_per_trade: float = 1.0,  # $1 per trade (or use percentage)
        commission_pct: float = 0.001,  # 0.1% commission
        slippage_pct: float = 0.001,  # 0.1% slippage
        max_positions: int = 10,
        max_position_pct: float = 0.10,  # 10% per position
        reserve_cash_pct: float = 0.05,  # Keep 5% cash reserve
    ):
        """
        Initialize portfolio backtest engine.
        
        Args:
            initial_capital: Starting capital
            commission_per_trade: Fixed commission per trade
            commission_pct: Commission as percentage of trade value
            slippage_pct: Slippage as percentage
            max_positions: Maximum concurrent positions
            max_position_pct: Maximum capital per position
            reserve_cash_pct: Cash reserve percentage
        """
        self.initial_capital = initial_capital
        self.commission_per_trade = commission_per_trade
        self.commission_pct = commission_pct
        self.slippage_pct = slippage_pct
        self.max_positions = max_positions
        self.max_position_pct = max_position_pct
        self.reserve_cash_pct = reserve_cash_pct
        
        # State
        self.cash = initial_capital
        self.equity = initial_capital
        self.positions: Dict[str, Position] = {}
        self.closed_trades: List[ClosedTrade] = []
        self.equity_curve: List[Tuple[datetime, float, float]] = []  # (date, equity, cash)
        self.daily_returns: List[float] = []
        
        # Risk tracking
        self.peak_equity = initial_capital
        self.max_drawdown = 0.0
        self.daily_losses = []  # Track for daily/weekly loss limits
    
    def can_open_position(self) -> bool:
        """Check if we can open a new position."""
        return len(self.positions) < self.max_positions
    
    def get_available_capital(self) -> float:
        """Get capital available for new positions."""
        reserve = self.equity * self.reserve_cash_pct
        return max(0, self.cash - reserve)
    
    def open_position(
        self,
        symbol: str,
        entry_date: datetime,
        entry_price: float,
        shares: int,
        stop_price: float
    ) -> bool:
        """
        Open a new position.
        
        Args:
            symbol: Stock symbol
            entry_date: Entry date
            entry_price: Entry price
            shares: Number of shares
            stop_price: Initial stop-loss price
            
        Returns:
            True if position opened successfully
        """
        if symbol in self.positions:
            return False  # Already have position in this symbol
        
        if not self.can_open_position():
            return False  # Max positions reached
        
        # Apply slippage (pay more when buying)
        actual_entry_price = entry_price * (1 + self.slippage_pct)
        
        # Calculate costs
        position_value = actual_entry_price * shares
        commission = max(
            self.commission_per_trade,
            position_value * self.commission_pct
        )
        total_cost = position_value + commission
        
        # Check if we have enough cash
        if total_cost > self.cash:
            # Reduce position size to fit available cash
            available = self.get_available_capital()
            if available < position_value * 0.5:  # Need at least 50% of desired position
                return False
            
            shares = int(available / (actual_entry_price * (1 + self.commission_pct)))
            if shares == 0:
                return False
            
            position_value = actual_entry_price * shares
            commission = max(self.commission_per_trade, position_value * self.commission_pct)
            total_cost = position_value + commission
        
        # Deduct cash
        self.cash -= total_cost
        
        # Create position
        position = Position(
            symbol=symbol,
            entry_date=entry_date,
            entry_price=actual_entry_price,
            shares=shares,
            stop_price=stop_price,
            entry_value=position_value
        )
        
        self.positions[symbol] = position
        return True
    
    def close_position(
        self,
        symbol: str,
        exit_date: datetime,
        exit_price: float,
        exit_reason: str
    ) -> bool:
        """
        Close an existing position.
        
        Args:
            symbol: Stock symbol
            exit_date: Exit date
            exit_price: Exit price
            exit_reason: Reason for exit
            
        Returns:
            True if position closed successfully
        """
        if symbol not in self.positions:
            return False
        
        position = self.positions[symbol]
        
        # Apply slippage (receive less when selling)
        actual_exit_price = exit_price * (1 - self.slippage_pct)
        
        # Calculate proceeds
        exit_value = actual_exit_price * position.shares
        commission = max(self.commission_per_trade, exit_value * self.commission_pct)
        net_proceeds = exit_value - commission
        
        # Add cash
        self.cash += net_proceeds
        
        # Calculate P&L
        pnl = net_proceeds - position.entry_value
        pnl_pct = pnl / position.entry_value
        
        # Create closed trade
        hold_days = (exit_date - position.entry_date).days
        trade = ClosedTrade(
            symbol=symbol,
            entry_date=position.entry_date,
            exit_date=exit_date,
            entry_price=position.entry_price,
            exit_price=actual_exit_price,
            shares=position.shares,
            pnl=pnl,
            pnl_pct=pnl_pct,
            exit_reason=exit_reason,
            hold_days=hold_days,
            entry_value=position.entry_value,
            exit_value=exit_value
        )
        
        self.closed_trades.append(trade)
        
        # Remove position
        del self.positions[symbol]
        
        return True
    
    def update_equity(self, current_date: datetime, current_prices: Dict[str, float]):
        """
        Update equity based on current prices.
        
        Args:
            current_date: Current date
            current_prices: Dict of symbol -> current price
        """
        # Update position values
        position_value = 0
        for symbol, position in self.positions.items():
            if symbol in current_prices:
                position.update(current_prices[symbol])
                position_value += position.current_value
        
        # Calculate total equity
        self.equity = self.cash + position_value
        
        # Track peak and drawdown
        if self.equity > self.peak_equity:
            self.peak_equity = self.equity
        
        current_drawdown = (self.peak_equity - self.equity) / self.peak_equity
        if current_drawdown > self.max_drawdown:
            self.max_drawdown = current_drawdown
        
        # Record equity curve
        self.equity_curve.append((current_date, self.equity, self.cash))
        
        # Calculate daily return
        if len(self.equity_curve) > 1:
            prev_equity = self.equity_curve[-2][1]
            daily_return = (self.equity - prev_equity) / prev_equity
            self.daily_returns.append(daily_return)
    
    def get_performance_metrics(self) -> Dict:
        """Calculate comprehensive performance metrics."""
        if not self.closed_trades:
            return {'error': 'No closed trades'}
        
        # Convert equity curve to DataFrame for calculations
        equity_df = pd.DataFrame(
            self.equity_curve,
            columns=['date', 'equity', 'cash']
        )
        equity_df.set_index('date', inplace=True)
        
        # Calculate returns
        total_return = (self.equity - self.initial_capital) / self.initial_capital
        
        # Time period
        start_date = self.equity_curve[0][0]
        end_date = self.equity_curve[-1][0]
        years = (end_date - start_date).days / 365.25
        
        # Annualized return
        if years > 0:
            annual_return = (1 + total_return) ** (1 / years) - 1
        else:
            annual_return = 0
        
        # Trade statistics
        trades_df = pd.DataFrame([t.to_dict() for t in self.closed_trades])
        
        winning_trades = trades_df[trades_df['pnl'] > 0]
        losing_trades = trades_df[trades_df['pnl'] <= 0]
        
        num_trades = len(trades_df)
        num_wins = len(winning_trades)
        num_losses = len(losing_trades)
        win_rate = num_wins / num_trades if num_trades > 0 else 0
        
        avg_win = winning_trades['pnl'].mean() if num_wins > 0 else 0
        avg_loss = losing_trades['pnl'].mean() if num_losses > 0 else 0
        
        total_wins = winning_trades['pnl'].sum() if num_wins > 0 else 0
        total_losses = abs(losing_trades['pnl'].sum()) if num_losses > 0 else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        avg_hold_days = trades_df['hold_days'].mean()
        
        # Sharpe ratio
        if len(self.daily_returns) > 1:
            daily_returns = np.array(self.daily_returns)
            sharpe_ratio = np.sqrt(252) * daily_returns.mean() / daily_returns.std() if daily_returns.std() > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Sortino ratio
        if len(self.daily_returns) > 1:
            downside_returns = [r for r in self.daily_returns if r < 0]
            if downside_returns:
                downside_std = np.std(downside_returns)
                sortino_ratio = np.sqrt(252) * np.mean(self.daily_returns) / downside_std if downside_std > 0 else 0
            else:
                sortino_ratio = sharpe_ratio
        else:
            sortino_ratio = 0
        
        # Calmar ratio
        calmar_ratio = abs(annual_return / self.max_drawdown) if self.max_drawdown > 0 else 0
        
        return {
            # Period
            'start_date': str(start_date.date()),
            'end_date': str(end_date.date()),
            'days': (end_date - start_date).days,
            'years': round(years, 2),
            
            # Returns
            'initial_capital': self.initial_capital,
            'final_equity': round(self.equity, 2),
            'total_return_pct': round(total_return * 100, 2),
            'annual_return_pct': round(annual_return * 100, 2),
            
            # Risk
            'sharpe_ratio': round(sharpe_ratio, 2),
            'sortino_ratio': round(sortino_ratio, 2),
            'calmar_ratio': round(calmar_ratio, 2),
            'max_drawdown_pct': round(self.max_drawdown * 100, 2),
            
            # Trades
            'total_trades': num_trades,
            'winning_trades': num_wins,
            'losing_trades': num_losses,
            'win_rate_pct': round(win_rate * 100, 2),
            'profit_factor': round(profit_factor, 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'total_wins': round(total_wins, 2),
            'total_losses': round(total_losses, 2),
            'avg_hold_days': round(avg_hold_days, 1),
            
            # Detailed trades
            'trades': [t.to_dict() for t in self.closed_trades],
            
            # Equity curve
            'equity_curve': equity_df.to_dict(),
        }
    
    def save_results(self, filepath: str):
        """Save backtest results to JSON file."""
        results = self.get_performance_metrics()
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)
    
    def print_summary(self):
        """Print performance summary."""
        metrics = self.get_performance_metrics()
        
        if 'error' in metrics:
            print(f"Error: {metrics['error']}")
            return
        
        print("\n" + "="*80)
        print("PORTFOLIO BACKTEST RESULTS")
        print("="*80)
        
        print(f"\n📅 Period: {metrics['start_date']} to {metrics['end_date']} ({metrics['days']} days)")
        
        print(f"\n💰 Returns:")
        print(f"   Initial Capital:  ${metrics['initial_capital']:,.2f}")
        print(f"   Final Equity:     ${metrics['final_equity']:,.2f}")
        print(f"   Total Return:     {metrics['total_return_pct']:+.2f}%")
        print(f"   Annual Return:    {metrics['annual_return_pct']:+.2f}%")
        
        print(f"\n📈 Risk Metrics:")
        print(f"   Sharpe Ratio:     {metrics['sharpe_ratio']:.2f}")
        print(f"   Sortino Ratio:    {metrics['sortino_ratio']:.2f}")
        print(f"   Calmar Ratio:     {metrics['calmar_ratio']:.2f}")
        print(f"   Max Drawdown:     {metrics['max_drawdown_pct']:.2f}%")
        
        print(f"\n📊 Trade Statistics:")
        print(f"   Total Trades:     {metrics['total_trades']}")
        print(f"   Winning Trades:   {metrics['winning_trades']} ({metrics['win_rate_pct']:.1f}%)")
        print(f"   Losing Trades:    {metrics['losing_trades']}")
        print(f"   Profit Factor:    {metrics['profit_factor']:.2f}")
        print(f"   Avg Win:          ${metrics['avg_win']:,.2f}")
        print(f"   Avg Loss:         ${metrics['avg_loss']:,.2f}")
        print(f"   Avg Hold:         {metrics['avg_hold_days']:.1f} days")
        
        print("\n" + "="*80)
