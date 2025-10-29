# AlphaFactory OS - Package #3: Advanced Strategies & Optimization

## 🎯 Overview

Package #3 builds upon the foundation established in Packages #1-2 to deliver professional-grade algorithmic trading strategies with sophisticated risk management, position sizing, and optimization capabilities.

## ✨ What's New in Package #3

### **Phase 1: Advanced Strategy Framework** ✅ COMPLETE

1. **Enhanced Strategy Base Class** (`strategy_base.py`)
   - Multiple position sizing methods (Fixed, Volatility-based, Kelly Criterion, Fixed Fractional)
   - Integrated risk management (stop-loss, take-profit, trailing stops)
   - ATR-based stops for volatility-adjusted exits
   - Signal filtering framework
   - Trade management logic

2. **RSI + MACD Combination Strategy** (`rsi_macd_strategy.py`)
   - Confluence-based entry signals
   - Three preset configurations (Conservative, Aggressive, Scalping)
   - Enhanced version with trend filters and ADX
   - Volume confirmation filters

3. **Bollinger Bands Strategies** (`bollinger_bands_strategy.py`)
   - Mean Reversion strategy (buy oversold, sell overbought)
   - Breakout strategy (trade continuation after squeezes)
   - Adaptive Combo strategy (switches based on market regime)
   - BB squeeze detection for optimal entry timing

4. **Enhanced Backtest Engine** (`enhanced_backtest_engine.py`)
   - Realistic intrabar stop checking
   - Slippage and commission modeling
   - Trade-level statistics (MAE, MFE)
   - Comprehensive performance metrics (Sharpe, Sortino, Calmar)
   - Detailed trade tracking and reporting

## 📦 Installation

### Files to Add to Your Project

Copy these files to your AlphaFactory project:

```bash
# Core framework files
src/strategies/strategy_base.py
src/strategies/rsi_macd_strategy.py
src/strategies/bollinger_bands_strategy.py
src/backtest/enhanced_backtest_engine.py

# Test/demo script
test_package3.py
```

### Dependencies

All dependencies are already included in your `requirements.txt` from Package #1. No additional installations needed!

## 🚀 Quick Start

### Example 1: Conservative RSI + MACD Strategy

```python
from strategy_base import PositionSizingMethod
from rsi_macd_strategy import RSI_MACD_Strategy, get_conservative_params
from enhanced_backtest_engine import EnhancedBacktestEngine

# Initialize strategy with conservative parameters
strategy = RSI_MACD_Strategy(
    rsi_period=14,
    rsi_oversold=25,
    rsi_overbought=75,
    **get_conservative_params(),
    position_sizing_method=PositionSizingMethod.FIXED
)

# Run backtest
engine = EnhancedBacktestEngine(
    initial_capital=100000,
    commission_pct=0.001,
    slippage_pct=0.0005
)

results = engine.run_backtest(strategy, data, symbol="AAPL")
print(f"Total Return: {results['total_return']:.2f}%")
print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
print(f"Max Drawdown: {results['max_drawdown']:.2f}%")
```

### Example 2: Volatility-Based Position Sizing

```python
# Use ATR-based position sizing for dynamic risk adjustment
strategy = RSI_MACD_Strategy(
    rsi_period=14,
    position_sizing_method=PositionSizingMethod.VOLATILITY_ATR,
    risk_per_trade=0.02,  # Risk 2% per trade
    use_atr_stops=True,
    atr_stop_multiplier=2.0
)

results = engine.run_backtest(strategy, data, symbol="AAPL")
```

### Example 3: Bollinger Bands Mean Reversion

```python
from bollinger_bands_strategy import BollingerBandsMeanReversion

strategy = BollingerBandsMeanReversion(
    bb_period=20,
    bb_std=2.0,
    volume_surge_ratio=1.5,
    exit_at_middle_band=True,
    stop_loss_pct=0.03,
    take_profit_pct=0.05
)

results = engine.run_backtest(strategy, data, symbol="AAPL")
```

## 📊 Position Sizing Methods

### 1. Fixed Position Sizing
```python
position_sizing_method=PositionSizingMethod.FIXED
position_size_pct=0.10  # 10% of capital per trade
```

### 2. Volatility-Based (ATR)
```python
position_sizing_method=PositionSizingMethod.VOLATILITY_ATR
risk_per_trade=0.02  # Risk 2% of capital
atr_stop_multiplier=2.0  # Stop at 2x ATR
```

### 3. Kelly Criterion
```python
position_sizing_method=PositionSizingMethod.KELLY_CRITERION
# Automatically calculates optimal position size based on win rate
```

### 4. Fixed Fractional
```python
position_sizing_method=PositionSizingMethod.FIXED_FRACTIONAL
risk_per_trade=0.015  # Risk 1.5% per trade
stop_loss_pct=0.02  # 2% stop loss
```

## 🛡️ Risk Management Features

### Stop-Loss Types

**1. Percentage-Based Stops**
```python
stop_loss_pct=0.02  # 2% stop loss
take_profit_pct=0.06  # 6% take profit
```

**2. ATR-Based Stops (Volatility-Adjusted)**
```python
use_atr_stops=True
atr_stop_multiplier=2.0  # Stop at 2x ATR distance
```

**3. Trailing Stops**
```python
trailing_stop_pct=0.015  # Trail by 1.5%
```

## 📈 Strategy Presets

### Conservative (Lower Risk, Steady Returns)
```python
from rsi_macd_strategy import get_conservative_params

params = get_conservative_params()
# RSI: 25/75 levels
# Stop: 2%, Take Profit: 6%
# Position Size: 5% of capital
```

### Aggressive (Higher Risk, Higher Potential)
```python
from rsi_macd_strategy import get_aggressive_params

params = get_aggressive_params()
# RSI: 35/65 levels
# Stop: 3%, Take Profit: 10%
# Position Size: 15% of capital
```

### Scalping (Quick Trades)
```python
from rsi_macd_strategy import get_scalping_params

params = get_scalping_params()
# RSI(7): 20/80 levels
# MACD(8,17,9)
# Stop: 1%, Take Profit: 2%
```

## 📊 Performance Metrics

The Enhanced Backtest Engine provides comprehensive metrics:

### Returns
- **Total Return**: Cumulative return over backtest period
- **Annual Return**: Annualized return rate
- **Final Equity**: Ending portfolio value

### Risk Metrics
- **Sharpe Ratio**: Risk-adjusted return (>1 is good, >2 is excellent)
- **Sortino Ratio**: Downside risk-adjusted return
- **Calmar Ratio**: Return vs. maximum drawdown
- **Max Drawdown**: Largest peak-to-trough decline

### Trade Statistics
- **Total Trades**: Number of completed trades
- **Win Rate**: Percentage of profitable trades
- **Profit Factor**: Gross profit / Gross loss
- **Avg Win/Loss**: Average profit/loss per trade
- **MAE/MFE**: Maximum Adverse/Favorable Excursion

## 🔧 Integration with Your AlphaFactory System

### Step 1: Update Your Project Structure

```
alphafactory/
├── src/
│   ├── strategies/
│   │   ├── __init__.py
│   │   ├── sma_crossover.py (from Package #2)
│   │   ├── strategy_base.py (NEW)
│   │   ├── rsi_macd_strategy.py (NEW)
│   │   └── bollinger_bands_strategy.py (NEW)
│   └── backtest/
│       ├── __init__.py
│       ├── backtest_engine.py (from Package #2)
│       └── enhanced_backtest_engine.py (NEW)
```

### Step 2: Use with Your Database

```python
from src.database.db_manager import DatabaseManager
from src.data.data_downloader import DataDownloader
from src.indicators.indicator_calculator import IndicatorCalculator
from src.strategies.rsi_macd_strategy import RSI_MACD_Strategy
from src.backtest.enhanced_backtest_engine import EnhancedBacktestEngine

# Load data from your database
db = DatabaseManager()
symbol = "AAPL"
bars = db.get_daily_bars(symbol, days=252)

# Calculate indicators
calc = IndicatorCalculator(bars)
calc.calculate_all()
data = calc.get_dataframe()

# Run strategy
strategy = RSI_MACD_Strategy(**get_conservative_params())
engine = EnhancedBacktestEngine(initial_capital=100000)
results = engine.run_backtest(strategy, data, symbol=symbol)

# Save to database
db.save_backtest_results(results)
```

## 🎮 Running the Demo

Test all strategies with the included demonstration:

```bash
py311 test_package3.py
```

This will:
1. Generate sample market data
2. Run 6 different strategy configurations
3. Compare performance across all strategies
4. Save results to `package3_results.json`

## 📋 Strategy Comparison Output

```
Strategy                            | Return     | Sharpe   | MaxDD    | Trades   | WinRate   | PF    
------------------------------------------------------------------------------------------------------
RSI14_MACD(12,26,9)                | +15.23%    | 1.45     | -8.12%   | 12       | 58.3%     | 1.87  
RSI_MACD_Enhanced_14               | +18.67%    | 1.72     | -6.45%   | 8        | 75.0%     | 2.34  
BB_MeanReversion_20_2.0std         | +12.45%    | 1.23     | -9.23%   | 24       | 54.2%     | 1.65  
BB_Breakout_20_2.0std              | +21.34%    | 1.89     | -7.89%   | 6        | 66.7%     | 2.12  
BB_Combo_20_2.0std                 | +16.78%    | 1.56     | -7.34%   | 18       | 61.1%     | 1.94  
```

## 🔄 Next Steps: Package #3 Remaining Phases

### Phase 2: Multi-Symbol Portfolio Engine
- Portfolio-level backtesting
- Correlation analysis
- Sector allocation
- Combined risk management

### Phase 3: Walk-Forward Optimization
- Parameter grid search
- Out-of-sample validation
- Overfitting detection
- Rolling window optimization

### Phase 4: Performance Visualization
- Equity curve charts
- Drawdown plots
- Strategy comparison dashboards
- Interactive performance reports

## 🆘 Troubleshooting

### "No trades executed"
- Check if your data has required indicators calculated
- Verify indicator names match strategy requirements
- Try more lenient signal thresholds (e.g., RSI 40/60 instead of 30/70)

### "Missing required indicators"
Ensure your data has these columns:
```python
# RSI + MACD strategies need:
'rsi_14', 'macd_12_26_9', 'macd_signal_12_26_9', 'macd_hist_12_26_9'

# Bollinger Bands strategies need:
'bb_upper_20_2.0', 'bb_middle_20_2.0', 'bb_lower_20_2.0'

# Position sizing needs:
'atr_14'  # For volatility-based sizing

# Filters may need:
'adx_14', 'sma_200'
```

### Performance Issues
- The enhanced engine checks stops on every bar (more realistic but slower)
- Disable intrabar stop checking for faster backtests:
```python
engine = EnhancedBacktestEngine(check_intrabar_stops=False)
```

## 📚 Further Reading

- **Risk Management**: See `strategy_base.py` for complete position sizing algorithms
- **Custom Strategies**: Inherit from `AdvancedStrategy` class to build your own
- **Optimization**: Stay tuned for Phase 3 (Walk-Forward Optimization)

## 🎉 Summary

Package #3 provides:
- ✅ 5+ professional trading strategies
- ✅ 4 position sizing methods
- ✅ Comprehensive risk management
- ✅ Realistic backtesting with slippage/commissions
- ✅ Detailed performance analytics
- ✅ Easy integration with your existing system

**You're now ready to build, test, and optimize sophisticated trading strategies!** 🚀

---

*Questions? Issues? Check the strategy parameter documentation in each module or run the demo for examples.*
