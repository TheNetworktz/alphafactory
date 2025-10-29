"""
Enhanced Backtest Engine for AlphaFactory OS
Package #3: Advanced Strategies

Improvements over basic engine:
- Proper stop-loss and take-profit execution
- Trailing stops
- Multiple position sizing methods
- Intrabar stop checking (realistic exits)
- Trade-level statistics
- Slippage and commission modeling
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json

from strategy_base import AdvancedStrategy, SignalType


class Trade:
    """Represents a single trade with entry/exit details."""
    
    def __init__(
        self,
        symbol: str,
        entry_date: datetime,
        entry_price: float,
        shares: int,
        direction: int,  # 1 for long, -1 for short
        stop_price: Optional[float] = None,
        take_profit_price: Optional[float] = None
    ):
        self.symbol = symbol
        self.entry_date = entry_date
        self.entry_price = entry_price
        self.shares = shares
        self.direction = direction
        self.stop_price = stop_price
        self.take_profit_price = take_profit_price
        
        self.exit_date: Optional[datetime] = None
        self.exit_price: Optional[float] = None
        self.exit_reason: Optional[str] = None
        self.pnl: Optional[float] = None
        self.pnl_pct: Optional[float] = None
        self.mae: float = 0  # Maximum Adverse Excursion
        self.mfe: float = 0  # Maximum Favorable Excursion
        
    def close(self, exit_date: datetime, exit_price: float, reason: str):
        """Close the trade."""
        self.exit_date = exit_date
        self.exit_price = exit_price
        self.exit_reason = reason
        
        if self.direction == 1:  # Long
            self.pnl = (exit_price - self.entry_price) * self.shares
            self.pnl_pct = (exit_price - self.entry_price) / self.entry_price
        else:  # Short
            self.pnl = (self.entry_price - exit_price) * self.shares
            self.pnl_pct = (self.entry_price - exit_price) / self.entry_price
    
    def update_mae_mfe(self, current_price: float):
        """Update maximum adverse/favorable excursion."""
        if self.direction == 1:  # Long
            excursion = (current_price - self.entry_price) / self.entry_price
        else:  # Short
            excursion = (self.entry_price - current_price) / self.entry_price
        
        self.mfe = max(self.mfe, excursion)
        self.mae = min(self.mae, excursion)
    
    def to_dict(self) -> Dict:
        """Convert trade to dictionary."""
        return {
            'symbol': self.symbol,
            'entry_date': self.entry_date,
            'entry_price': self.entry_price,
            'exit_date': self.exit_date,
            'exit_price': self.exit_price,
            'shares': self.shares,
            'direction': 'LONG' if self.direction == 1 else 'SHORT',
            'pnl': self.pnl,
            'pnl_pct': self.pnl_pct * 100 if self.pnl_pct else None,
            'exit_reason': self.exit_reason,
            'stop_price': self.stop_price,
            'take_profit_price': self.take_profit_price,
            'mae': self.mae * 100 if self.mae else 0,
            'mfe': self.mfe * 100 if self.mfe else 0,
        }


class EnhancedBacktestEngine:
    """
    Enhanced backtesting engine with realistic trade execution.
    """
    
    def __init__(
        self,
        initial_capital: float = 100000.0,
        commission_pct: float = 0.001,  # 0.1% commission
        slippage_pct: float = 0.0005,   # 0.05% slippage
        check_intrabar_stops: bool = True
    ):
        """
        Initialize backtest engine.
        
        Args:
            initial_capital: Starting capital
            commission_pct: Commission as percentage of trade value
            slippage_pct: Slippage as percentage of entry price
            check_intrabar_stops: Check if stops hit within bar (more realistic)
        """
        self.initial_capital = initial_capital
        self.commission_pct = commission_pct
        self.slippage_pct = slippage_pct
        self.check_intrabar_stops = check_intrabar_stops
        
        self.reset()
    
    def reset(self):
        """Reset backtest state."""
        self.equity = self.initial_capital
        self.cash = self.initial_capital
        self.positions: Dict[str, Trade] = {}
        self.closed_trades: List[Trade] = []
        self.equity_curve: List[Tuple[datetime, float]] = []
    
    def run_backtest(
        self,
        strategy: AdvancedStrategy,
        data: pd.DataFrame,
        symbol: str = "UNKNOWN"
    ) -> Dict:
        """
        Run backtest for a strategy on given data.
        
        Args:
            strategy: Strategy instance
            data: DataFrame with OHLCV and indicators
            symbol: Trading symbol
            
        Returns:
            Dictionary with backtest results
        """
        self.reset()
        
        # Generate signals
        signals = strategy.generate_signals(data)
        signals = strategy.apply_filters(data, signals)
        
        # Iterate through data
        for i in range(len(data)):
            current_date = data.index[i]
            current_row = data.iloc[i]
            current_signal = signals.iloc[i]
            
            open_price = current_row['open']
            high_price = current_row['high']
            low_price = current_row['low']
            close_price = current_row['close']
            atr = current_row.get('atr_14', None)
            
            # Check existing positions for stops
            if symbol in self.positions:
                position = self.positions[symbol]
                
                # Update MAE/MFE
                position.update_mae_mfe(close_price)
                
                # Check if stops hit during the bar
                if self.check_intrabar_stops:
                    stop_hit = False
                    
                    if position.direction == 1:  # Long position
                        # Check stop-loss
                        if position.stop_price and low_price <= position.stop_price:
                            exit_price = position.stop_price
                            self._close_position(symbol, current_date, exit_price, "Stop Loss")
                            stop_hit = True
                        # Check take-profit
                        elif position.take_profit_price and high_price >= position.take_profit_price:
                            exit_price = position.take_profit_price
                            self._close_position(symbol, current_date, exit_price, "Take Profit")
                            stop_hit = True
                    
                    else:  # Short position
                        # Check stop-loss
                        if position.stop_price and high_price >= position.stop_price:
                            exit_price = position.stop_price
                            self._close_position(symbol, current_date, exit_price, "Stop Loss")
                            stop_hit = True
                        # Check take-profit
                        elif position.take_profit_price and low_price <= position.take_profit_price:
                            exit_price = position.take_profit_price
                            self._close_position(symbol, current_date, exit_price, "Take Profit")
                            stop_hit = True
                    
                    if stop_hit:
                        current_signal = 0  # Don't process new signal if stop hit
                
                # Update trailing stops
                if symbol in self.positions and strategy.trailing_stop_pct:
                    position = self.positions[symbol]
                    new_stop = strategy.update_trailing_stop(
                        symbol,
                        close_price,
                        SignalType.LONG if position.direction == 1 else SignalType.SHORT
                    )
                    if new_stop:
                        position.stop_price = new_stop
            
            # Process new signals
            if current_signal == 1:  # LONG signal
                # Close any short position first
                if symbol in self.positions and self.positions[symbol].direction == -1:
                    self._close_position(symbol, current_date, close_price, "Signal Reversal")
                
                # Open new long position
                if symbol not in self.positions:
                    self._open_position(
                        symbol, current_date, close_price, 1,
                        strategy, atr
                    )
            
            elif current_signal == -1:  # SHORT signal
                # Close any long position first
                if symbol in self.positions and self.positions[symbol].direction == 1:
                    self._close_position(symbol, current_date, close_price, "Signal Reversal")
                
                # Open new short position
                if symbol not in self.positions:
                    self._open_position(
                        symbol, current_date, close_price, -1,
                        strategy, atr
                    )
            
            elif current_signal == 2:  # EXIT_LONG
                if symbol in self.positions and self.positions[symbol].direction == 1:
                    self._close_position(symbol, current_date, close_price, "Exit Signal")
            
            elif current_signal == -2:  # EXIT_SHORT
                if symbol in self.positions and self.positions[symbol].direction == -1:
                    self._close_position(symbol, current_date, close_price, "Exit Signal")
            
            # Update equity curve
            self._update_equity(current_date, close_price)
        
        # Close any remaining positions at end
        if self.positions:
            final_date = data.index[-1]
            final_price = data.iloc[-1]['close']
            for sym in list(self.positions.keys()):
                self._close_position(sym, final_date, final_price, "End of Backtest")
        
        # Calculate performance metrics
        return self._calculate_performance(data, strategy)
    
    def _open_position(
        self,
        symbol: str,
        date: datetime,
        price: float,
        direction: int,
        strategy: AdvancedStrategy,
        atr: Optional[float] = None
    ):
        """Open a new position."""
        # Calculate position size
        shares = strategy.calculate_position_size(
            symbol=symbol,
            price=price,
            equity=self.equity,
            volatility=atr
        )
        
        if shares <= 0:
            return
        
        # Apply slippage
        entry_price = price * (1 + self.slippage_pct * direction)
        
        # Calculate stops
        signal_type = SignalType.LONG if direction == 1 else SignalType.SHORT
        stop_price, tp_price = strategy.calculate_stops(symbol, entry_price, signal_type, atr)
        
        # Calculate cost
        position_cost = entry_price * shares
        commission = position_cost * self.commission_pct
        total_cost = position_cost + commission
        
        if total_cost > self.cash:
            # Not enough cash, reduce position size
            available_cash = self.cash * 0.95  # Leave some buffer
            shares = int(available_cash / (entry_price * (1 + self.commission_pct)))
            if shares <= 0:
                return
            position_cost = entry_price * shares
            commission = position_cost * self.commission_pct
            total_cost = position_cost + commission
        
        # Update cash
        self.cash -= total_cost
        
        # Create trade
        trade = Trade(
            symbol=symbol,
            entry_date=date,
            entry_price=entry_price,
            shares=shares,
            direction=direction,
            stop_price=stop_price,
            take_profit_price=tp_price
        )
        
        self.positions[symbol] = trade
    
    def _close_position(
        self,
        symbol: str,
        date: datetime,
        price: float,
        reason: str
    ):
        """Close an existing position."""
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        
        # Apply slippage
        exit_price = price * (1 - self.slippage_pct * position.direction)
        
        # Close trade
        position.close(date, exit_price, reason)
        
        # Calculate proceeds
        proceeds = exit_price * position.shares
        commission = proceeds * self.commission_pct
        net_proceeds = proceeds - commission
        
        # Update cash
        if position.direction == 1:  # Long
            self.cash += net_proceeds
        else:  # Short
            # For short, we get back the collateral plus profit/loss
            original_value = position.entry_price * position.shares
            profit = (position.entry_price - exit_price) * position.shares
            self.cash += original_value + profit - commission
        
        # Move to closed trades
        self.closed_trades.append(position)
        del self.positions[symbol]
    
    def _update_equity(self, date: datetime, price: float):
        """Update equity curve."""
        # Cash + value of open positions
        position_value = 0
        for symbol, position in self.positions.items():
            if position.direction == 1:  # Long
                position_value += price * position.shares
            else:  # Short
                # Short value = collateral + unrealized P&L
                position_value += position.entry_price * position.shares
                position_value += (position.entry_price - price) * position.shares
        
        self.equity = self.cash + position_value
        self.equity_curve.append((date, self.equity))
    
    def _calculate_performance(
        self,
        data: pd.DataFrame,
        strategy: AdvancedStrategy
    ) -> Dict:
        """Calculate comprehensive performance metrics."""
        if not self.closed_trades:
            return {
                'error': 'No trades executed',
                'initial_capital': self.initial_capital,
                'final_equity': self.equity
            }
        
        # Convert equity curve to DataFrame
        equity_df = pd.DataFrame(self.equity_curve, columns=['date', 'equity'])
        equity_df.set_index('date', inplace=True)
        
        # Returns
        total_return = (self.equity - self.initial_capital) / self.initial_capital
        
        # Trade statistics
        trade_returns = [t.pnl_pct for t in self.closed_trades]
        winning_trades = [t for t in self.closed_trades if t.pnl > 0]
        losing_trades = [t for t in self.closed_trades if t.pnl <= 0]
        
        win_rate = len(winning_trades) / len(self.closed_trades) if self.closed_trades else 0
        
        avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        
        # Drawdown calculation
        equity_curve_series = equity_df['equity']
        rolling_max = equity_curve_series.expanding().max()
        drawdown = (equity_curve_series - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        # Sharpe ratio (assuming 252 trading days)
        returns = equity_curve_series.pct_change().dropna()
        if len(returns) > 0:
            sharpe_ratio = np.sqrt(252) * returns.mean() / returns.std() if returns.std() != 0 else 0
        else:
            sharpe_ratio = 0
        
        # Sortino ratio (downside deviation)
        downside_returns = returns[returns < 0]
        if len(downside_returns) > 0:
            downside_std = downside_returns.std()
            sortino_ratio = np.sqrt(252) * returns.mean() / downside_std if downside_std != 0 else 0
        else:
            sortino_ratio = 0
        
        # Calmar ratio
        years = (data.index[-1] - data.index[0]).days / 365.25
        annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
        calmar_ratio = abs(annual_return / max_drawdown) if max_drawdown != 0 else 0
        
        # MAE/MFE analysis
        avg_mae = np.mean([t.mae for t in self.closed_trades])
        avg_mfe = np.mean([t.mfe for t in self.closed_trades])
        
        return {
            'strategy_name': strategy.name,
            'symbol': self.closed_trades[0].symbol if self.closed_trades else 'N/A',
            'start_date': data.index[0].strftime('%Y-%m-%d'),
            'end_date': data.index[-1].strftime('%Y-%m-%d'),
            'trading_days': len(data),
            
            # Capital metrics
            'initial_capital': self.initial_capital,
            'final_equity': self.equity,
            'total_return': total_return * 100,
            'annual_return': annual_return * 100,
            
            # Risk metrics
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio,
            'max_drawdown': max_drawdown * 100,
            
            # Trade statistics
            'total_trades': len(self.closed_trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate * 100,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'avg_mae': avg_mae * 100,
            'avg_mfe': avg_mfe * 100,
            
            # Detailed trades
            'trades': [t.to_dict() for t in self.closed_trades],
            'equity_curve': equity_df.to_dict()['equity'],
            'strategy_parameters': strategy.get_parameters()
        }
