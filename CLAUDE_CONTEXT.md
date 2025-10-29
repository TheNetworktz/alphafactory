# AlphaFactory OS - Complete Technical Context for Continuation

## 🔧 CRITICAL TECHNICAL DETAILS

### Python Environment
- **Command:** `py311` (NOT `python` or `py`)
- **Full path:** `D:\Python311\python.exe`
- **Version:** Python 3.11.9 (64-bit)
- **Why:** We have Python 3.13 also installed, must use 3.11 specifically

### Python Path Setup Pattern (CRITICAL!)
**Every module file must start with this:**
```python
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent  # Adjust based on depth
sys.path.insert(0, str(project_root))

# Then imports work:
from src.config.config_loader import config
from src.database.db_manager import db_manager
```

**Why:** Project uses `src/` package structure, not installed package

### Running Files
```powershell
# WRONG (will fail):
python script.py
py script.py

# CORRECT:
py311 script.py
py311 run.py
py311 -m src.module.file

# For testing modules directly:
cd D:\AI_PROJECTS\alphafactory
py311 src/strategies/stm.py
```

### Database Connection
**Password contains @ symbol - MUST be URL encoded:**
```python
# .env file:
DB_PASSWORD=T@l09201997

# DATABASE_URL in .env:
DATABASE_URL=postgresql://postgres:T%40l09201997@localhost:5432/alphafactory
                                    ^^^^
                                    @ becomes %40

# Python code (loads from .env):
from src.config.config_loader import config
db_url = config.database_url  # Automatically loaded from .env
```

**Common mistake:** Forgetting %40 encoding causes "host not found" error

---

## 📦 PROJECT STRUCTURE (EXACT)
```
D:\AI_PROJECTS\alphafactory\
├── .env                    # API keys (NOT in Git - has @ as %40 in URLs)
├── .env.example            # Template (safe to commit)
├── .gitignore              # Excludes: .env, logs/, data/, results/, __pycache__/
├── README.md
├── ROADMAP.md              # Full project plan
├── requirements.txt        # 126 packages
├── global_config.yaml      # Non-sensitive config (UTF-8 encoded!)
├── run.py                  # Helper: sets PYTHONPATH, loads .env
├── run_first_backtest.py   # Example backtest workflow
├── test_connections.py     # Validates DB, Redis, APIs
├── verify_install.py       # Checks package installation
│
├── src/                    # Main codebase
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── config_loader.py      # Loads .env + YAML, provides config object
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py              # SQLAlchemy ORM (7 tables)
│   │   └── db_manager.py          # Session management, context manager
│   ├── data/
│   │   ├── __init__.py
│   │   └── data_downloader.py     # Multi-source: Polygon, AV, Yahoo
│   ├── indicators/
│   │   ├── __init__.py
│   │   └── indicator_calculator.py # 38 TA-Lib indicators
│   ├── strategies/
│   │   ├── __init__.py
│   │   └── sma_crossover.py       # Example strategy (pattern to follow)
│   ├── backtest/
│   │   ├── __init__.py
│   │   └── backtest_engine.py     # Vectorized single-symbol backtesting
│   └── utils/
│       └── __init__.py
│
├── data/                   # Downloaded market data (NOT in Git)
├── logs/                   # Application logs (NOT in Git)
├── results/                # Backtest results CSVs (NOT in Git)
├── models/                 # Future ML models
└── tests/                  # Unit/integration tests
    ├── __init__.py
    ├── unit/
    └── integration/
```

---

## 🗄️ DATABASE SCHEMA (PostgreSQL)

### Connection Details:
- **Host:** localhost
- **Port:** 5432
- **Database:** alphafactory
- **User:** postgres
- **Password:** T@l09201997 (in URL: T%40l09201997)

### Tables (SQLAlchemy Models):

#### 1. `symbols` (Stock Metadata)
```python
class Symbol(Base):
    id = Integer (PK, autoincrement)
    symbol = String(10) (unique, indexed)
    name = String(255)
    exchange = String(50)
    sector = String(100)
    industry = String(100)
    market_cap = Float
    is_active = Boolean (default=True)
    created_at = DateTime
    updated_at = DateTime
```

#### 2. `daily_bars` (OHLCV + Indicators)
```python
class DailyBar(Base):
    id = Integer (PK, autoincrement)
    symbol_id = Integer (FK to symbols.id)
    date = DateTime (indexed)
    open, high, low, close, volume = Float
    adj_close = Float
    
    # Pre-calculated indicators (cached for performance):
    sma_20, sma_50, sma_200 = Float
    rsi_14 = Float
    macd, macd_signal = Float
    bbands_upper, bbands_middle, bbands_lower = Float
    
    # Unique constraint: (symbol_id, date)
    # Index: (symbol_id, date) for fast queries
```

#### 3. `strategies` (Strategy Definitions)
```python
class Strategy(Base):
    id = Integer (PK)
    name = String(100) (unique, indexed)
    description = Text
    version = String(20)
    parameters = Text (JSON string)
    is_active = Boolean
    created_at, updated_at = DateTime
```

#### 4. `backtests` (Backtest Results)
```python
class Backtest(Base):
    id = Integer (PK)
    strategy_id = Integer (FK)
    name = String(255)
    start_date, end_date = DateTime
    initial_capital = Float
    
    # Performance metrics:
    final_equity, total_return, annual_return = Float
    sharpe_ratio, sortino_ratio = Float
    max_drawdown = Float
    win_rate, profit_factor = Float
    total_trades, winning_trades, losing_trades = Integer
    commission_total, slippage_total = Float
    
    status = String(20) # pending/running/completed/failed
    error_message = Text
    created_at, completed_at = DateTime
```

#### 5. `trades` (Individual Trades)
```python
class Trade(Base):
    id = Integer (PK)
    strategy_id = Integer (FK)
    backtest_id = Integer (FK, nullable for live trades)
    symbol_id = Integer (FK)
    
    trade_type = String(10) # LONG/SHORT
    entry_date, entry_price, entry_quantity = DateTime, Float, Float
    exit_date, exit_price, exit_quantity = DateTime, Float, Float
    exit_reason = String(50) # stop_loss/take_profit/signal/manual
    
    gross_pnl, commission, slippage, net_pnl = Float
    return_pct = Float
    signal_strength = Float (0-1 confidence)
    notes = Text
    is_live = Boolean
    created_at, updated_at = DateTime
```

#### 6. `performance_snapshots` (Daily Portfolio Metrics)
```python
class PerformanceSnapshot(Base):
    id = Integer (PK)
    date = DateTime (indexed)
    strategy_id = Integer (FK, nullable)
    backtest_id = Integer (FK, nullable)
    
    equity, cash, positions_value = Float
    daily_return, cumulative_return, drawdown = Float
    volatility, sharpe_ratio, beta = Float
    num_positions = Integer
    largest_position_pct = Float
    is_live = Boolean
```

#### 7. `earnings_calendar` (Earnings Dates)
```python
class EarningsCalendar(Base):
    id = Integer (PK)
    symbol_id = Integer (FK)
    earnings_date = DateTime (indexed)
    fiscal_quarter = String(10)
    estimate_eps, actual_eps, surprise_pct = Float
```

### Database Session Pattern:
```python
from src.database.db_manager import db_manager

# Initialize once at startup:
db_manager.initialize()

# Use context manager for queries:
with db_manager.get_session() as session:
    # Query data
    bars = session.query(DailyBar).filter_by(symbol_id=1).all()
    
    # Add data
    new_bar = DailyBar(symbol_id=1, date=date, close=100.0, ...)
    session.add(new_bar)
    
    # session.commit() happens automatically on context exit
```

---

## 🔑 CONFIGURATION SYSTEM

### Config Loader Pattern:
```python
from src.config.config_loader import config

# Environment variables (from .env):
config.trading_mode          # "paper" or "live"
config.polygon_api_key       # Polygon.io API key
config.alpha_vantage_api_key # Alpha Vantage API key
config.database_url          # PostgreSQL connection string

# YAML config (from global_config.yaml):
config.parallel_jobs         # 24 (for your 32-core CPU)
config.data_dir              # Path object: D:\AI_PROJECTS\alphafactory\data
config.log_dir               # Path object: D:\AI_PROJECTS\alphafactory\logs
config.get_yaml('system', 'max_memory_gb')  # 200

# Common properties:
config.is_paper_trading      # True if TRADING_MODE=paper
config.backtest_initial_capital  # 100000.0
config.backtest_commission_per_share  # 0.005
```

### YAML Access Pattern:
```python
# Nested access:
value = config.get_yaml('section', 'subsection', 'key', default=None)

# Examples:
parallel = config.get_yaml('system', 'parallel_jobs')  # 24
rate = config.get_yaml('data', 'sources', 'polygon', 'rate_limit')  # 5
```

---

## 📊 INDICATOR CALCULATOR USAGE

### Available Indicators (38 total):
```python
from src.indicators.indicator_calculator import IndicatorCalculator

calc = IndicatorCalculator()

# Load data with all indicators:
df = calc.load_data_with_indicators('AAPL', '2024-01-01', '2025-01-01')

# Returns DataFrame with these columns:
# OHLCV: open, high, low, close, volume, adj_close
# Moving Averages: sma_20, sma_50, sma_200, ema_12, ema_26
# Momentum: rsi_14, rsi_7, macd, macd_signal, macd_hist, stoch_k, stoch_d, williams_r, roc
# Volatility: bb_upper, bb_middle, bb_lower, bb_width, atr_14, std_20
# Volume: obv, ad, adosc
# Trend: adx, sar
# Patterns: cdl_doji, cdl_hammer, cdl_engulfing, cdl_morning_star, cdl_evening_star
# Derived: price_to_sma20, price_to_sma50, price_to_sma200, sma_20_above_50, sma_50_above_200, bb_position, rsi_overbought, rsi_oversold

# Calculate on custom DataFrame:
df_with_indicators = calc.calculate_all_indicators(df, save_to_db=False)
```

---

## 📈 STRATEGY PATTERN (CRITICAL!)

### Base Pattern (from sma_crossover.py):
```python
class StrategyName:
    """
    Strategy description
    """
    
    def __init__(self, param1: int, param2: int):
        self.param1 = param1
        self.param2 = param2
        self.name = f"StrategyName_{param1}_{param2}"
        
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
        
        # Initialize signal column
        df['signal'] = 0  # 0 = no position, 1 = long, -1 = short
        
        # Generate signals based on strategy logic
        # Example: df.loc[condition, 'signal'] = 1
        
        # Calculate position changes (for entry/exit detection)
        df['position'] = df['signal'].diff()
        
        # Mark entry and exit points
        df['entry'] = 0
        df['exit'] = 0
        df.loc[df['position'] > 0, 'entry'] = 1  # Entry signal
        df.loc[df['position'] < 0, 'exit'] = 1   # Exit signal
        
        return df
    
    def get_parameters(self) -> dict:
        """Get strategy parameters"""
        return {
            'name': self.name,
            'param1': self.param1,
            'param2': self.param2
        }
```

### Signal DataFrame Structure:
```python
# Input DataFrame (from indicator_calculator):
df.columns = ['date', 'open', 'high', 'low', 'close', 'volume', 
              'sma_20', 'sma_50', 'rsi_14', 'macd', ...]

# Output DataFrame (after generate_signals):
df.columns = [...all input columns..., 
              'signal',    # 0/1/-1 (flat/long/short)
              'position',  # signal.diff() for change detection
              'entry',     # 1 when entering position, else 0
              'exit']      # 1 when exiting position, else 0
```

---

## 🔬 BACKTEST ENGINE USAGE

### Current Engine (Single Symbol):
```python
from src.backtest.backtest_engine import BacktestEngine

# Initialize engine
engine = BacktestEngine(
    initial_capital=100000,
    commission_pct=0.001,    # 0.1% commission
    slippage_pct=0.0005      # 0.05% slippage
)

# Run backtest
results = engine.run(
    df_with_signals,         # DataFrame with 'signal' column
    position_size=0.95       # Use 95% of capital
)

# Results dictionary contains:
results = {
    'initial_capital': 100000,
    'final_equity': 125866.49,
    'total_return': 25.87,        # Percentage
    'annual_return': 25.97,       # Percentage
    'volatility': 19.55,          # Annualized %
    'sharpe_ratio': 1.33,
    'sortino_ratio': 1.46,
    'max_drawdown': -11.70,       # Percentage
    'calmar_ratio': 2.22,
    'num_trades': 3,
    'win_rate': 0.0,              # Percentage
    'avg_win': 0.0,
    'avg_loss': -4839.42,
    'profit_factor': 0.0,
    'days': 364,
    'years': 1.0,
    'df': DataFrame,              # With equity curve
    'trades': [...]               # List of trade dicts
}

# Print formatted results
engine.print_results(results)

# Access equity curve
equity_df = results['df'][['equity', 'returns', 'cash', 'holdings']]
```

### Trade Dictionary Structure:
```python
trade = {
    'entry_date': datetime,
    'exit_date': datetime,
    'entry_price': 236.97,
    'exit_price': 229.75,
    'shares': 400.5,
    'pnl': -2987.93,
    'return_pct': -3.05
}
```

---

## 📥 DATA DOWNLOADER USAGE

### Download Pattern:
```python
from src.data.data_downloader import DataDownloader

downloader = DataDownloader()

# Download and save to database (one step):
success = downloader.download_and_save(
    symbol='AAPL',
    start_date='2024-01-01',
    end_date='2025-01-01',
    source='auto'  # or 'polygon', 'alpha_vantage', 'yfinance'
)

# Just download (no DB save):
df = downloader.download_daily_bars(
    symbol='AAPL',
    start_date='2024-01-01',
    end_date='2025-01-01',
    source='auto'
)

# Data source priority (auto mode):
# 1. Polygon.io (if API key present) - BEST quality
# 2. Alpha Vantage (if API key present)
# 3. Yahoo Finance (always available, free backup)
```

### DataFrame Structure from Downloader:
```python
# Returned DataFrame columns:
df.index = DatetimeIndex (date column as index)
df.columns = ['open', 'high', 'low', 'close', 'volume', 'adj_close']
```

---

## 🔄 COMMON WORKFLOWS

### Workflow 1: Add New Strategy
```python
# 1. Create strategy file: src/strategies/new_strategy.py
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.strategies.base_pattern import BaseStrategy  # Follow SMA pattern

class NewStrategy:
    def __init__(self, params):
        # Initialize
        pass
    
    def generate_signals(self, df):
        # Signal logic
        return df

# 2. Test strategy:
if __name__ == '__main__':
    from src.database.db_manager import db_manager
    from src.indicators.indicator_calculator import IndicatorCalculator
    
    db_manager.initialize()
    calc = IndicatorCalculator()
    
    df = calc.load_data_with_indicators('AAPL', '2024-01-01', '2025-01-01')
    strategy = NewStrategy(params)
    df = strategy.generate_signals(df)
    
    # Run backtest
    from src.backtest.backtest_engine import BacktestEngine
    engine = BacktestEngine()
    results = engine.run(df)
    engine.print_results(results)
```

### Workflow 2: Run Complete Backtest
```python
# Can use run.py or standalone script
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.database.db_manager import db_manager
from src.data.data_downloader import DataDownloader
from src.indicators.indicator_calculator import IndicatorCalculator
from src.strategies.strategy_name import StrategyName
from src.backtest.backtest_engine import BacktestEngine

def main():
    # Initialize
    db_manager.initialize()
    downloader = DataDownloader()
    calc = IndicatorCalculator()
    
    # Download data
    downloader.download_and_save('AAPL', '2023-01-01', '2025-01-01')
    
    # Load with indicators
    df = calc.load_data_with_indicators('AAPL', '2023-01-01', '2025-01-01')
    
    # Generate signals
    strategy = StrategyName(param1, param2)
    df = strategy.generate_signals(df)
    
    # Backtest
    engine = BacktestEngine(initial_capital=100000)
    results = engine.run(df, position_size=0.95)
    
    # Display
    engine.print_results(results)
    
    # Save results
    results['df'].to_csv(f'results/backtest_{symbol}.csv')

if __name__ == '__main__':
    main()
```

---

## ⚠️ COMMON PITFALLS & SOLUTIONS

### Pitfall 1: Import Errors
```python
# WRONG:
from config.config_loader import config  # ModuleNotFoundError

# CORRECT:
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
from src.config.config_loader import config
```

### Pitfall 2: Database Connection
```python
# WRONG:
DATABASE_URL=postgresql://postgres:T@l09201997@localhost:5432/alphafactory
# Error: "could not translate host name l09201997@localhost"

# CORRECT:
DATABASE_URL=postgresql://postgres:T%40l09201997@localhost:5432/alphafactory
                                    ^^^^
```

### Pitfall 3: DataFrame Index
```python
# Data from downloader has DatetimeIndex
df.index  # DatetimeIndex

# When iterating in backtest:
for i in range(1, len(df)):
    date = df.index[i]  # Use index, not df['date']
    price = df.loc[date, 'close']  # Use .loc with index
```

### Pitfall 4: NaN Values in Indicators
```python
# Indicators have NaN for initial bars
df['sma_50'].iloc[0:49]  # All NaN (need 50 bars)

# Always check for NaN before using:
if not pd.isna(df.loc[date, 'sma_50']):
    # Use indicator
    pass
```

### Pitfall 5: Signal vs Position
```python
# 'signal' = current state (1 = long, 0 = flat)
# 'position' = signal.diff() = CHANGE in state

# For entry detection:
df.loc[df['position'] > 0, 'entry'] = 1  # Signal changed to 1

# For exit detection:
df.loc[df['position'] < 0, 'exit'] = 1   # Signal changed from 1
```

---

## 🎯 CURRENT DATA STATUS

### Loaded Data:
```python
# AAPL: 250 bars (2024-10-29 to 2025-10-29)
# - All 38 indicators calculated and cached
# - In PostgreSQL daily_bars table
# - Ready for backtesting
```

### To Download More:
```python
symbols = ['MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA']
for symbol in symbols:
    downloader.download_and_save(symbol, '2023-01-01', '2025-01-01')
```

---

## 💻 DEVELOPMENT COMMANDS
```powershell
# Navigate to project:
cd D:\AI_PROJECTS\alphafactory

# Run any script:
py311 script.py

# Run module directly (for testing):
py311 src/strategies/stm.py

# Test database connection:
py311 test_connections.py

# Verify packages installed:
py311 verify_install.py

# Run backtest:
py311 run_first_backtest.py

# Check Git status:
git status

# Commit changes:
git add .
git commit -m "Your message"
git push
```

---

## 📦 KEY DEPENDENCIES & VERSIONS
```
Python: 3.11.9
pandas: 2.1.3
numpy: 1.26.4
TA-Lib: 0.4.28
SQLAlchemy: 2.0.23
psycopg2-binary: 2.9.9
redis: 5.0.1
polygon-api-client: 1.13.2
alpha-vantage: 2.3.1
yfinance: 0.2.32
scikit-learn: 1.3.2
xgboost: 2.0.2
lightgbm: 4.1.0
plotly: 5.18.0
loguru: 0.7.2
```

---

## 🚨 ABSOLUTELY CRITICAL REMINDERS

1. **ALWAYS use `py311` command** (not python, not py)
2. **ALWAYS add project root to sys.path** in every module
3. **ALWAYS encode @ as %40** in DATABASE_URL
4. **ALWAYS check for NaN** in indicators before using
5. **ALWAYS use .copy()** on DataFrames before modifying
6. **ALWAYS use context manager** for database sessions
7. **NEVER commit .env file** to Git (has API keys)
8. **NEVER use localStorage** in artifacts (not supported)

---

## 📊 PERFORMANCE METRICS REFERENCE
```python
# Sharpe Ratio: (Annual Return - Risk Free Rate) / Volatility
# Good: > 1.0, Great: > 2.0

# Sortino Ratio: (Annual Return - Risk Free Rate) / Downside Volatility
# Good: > 1.5

# Max Drawdown: Largest peak-to-trough decline
# Good: < 20%, Great: < 10%

# Win Rate: Winning Trades / Total Trades
# Mean reversion target: > 60%
# Trend following typical: 40-50%

# Profit Factor: Gross Profit / Gross Loss
# Good: > 1.5, Great: > 2.0

# Calmar Ratio: Annual Return / Max Drawdown
# Good: > 1.0, Great: > 2.0
```

---

## 🎯 SUCCESS CRITERIA FOR STM

### Backtest Requirements:
- Sharpe Ratio > 1.5
- Win Rate > 60%
- Profit Factor > 2.0
- Max Drawdown < 15%
- Minimum 50 trades (statistical significance)

### Paper Trading Requirements:
- 90+ consecutive days
- Performance within 5% of backtest
- Zero execution errors
- All risk limits respected

---

**CRITICAL: This document contains ALL technical context needed. Paste this entire file at the start of any new conversation to ensure seamless continuation.**

**Last Updated:** 2025-10-29  
**Version:** 1.0  
**Status:** Package #1-2 Complete, Package #3 (STM) Next
```

---

## 🎯 FINAL NEW CONVERSATION PROMPT

**Paste THIS at the start of your new conversation (it includes the context file above):**
```
I'm continuing development of AlphaFactory OS. I completed Packages #1-2 in a previous conversation. Here's the complete technical context:

[Paste the entire CLAUDE_CONTEXT.md file above]

IMMEDIATE GOAL:
Build STM (Short-Term Mean Reversion) strategy as Phase 1 to generate quick profits before scaling to HTF Portfolio strategy.

Ready to start Package #3: STM Strategy implementation!