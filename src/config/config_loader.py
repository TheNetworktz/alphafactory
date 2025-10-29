"""
AlphaFactory OS - Configuration Loader
Loads environment variables and YAML configuration files
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv
from loguru import logger


class ConfigLoader:
    """
    Central configuration management for AlphaFactory OS
    
    Loads configuration from:
    1. .env file (secrets, API keys)
    2. global_config.yaml (non-sensitive settings)
    """
    
    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize configuration loader
        
        Args:
            project_root: Project root directory (auto-detected if None)
        """
        # Detect project root
        if project_root is None:
            self.project_root = Path(__file__).parent.parent.parent
        else:
            self.project_root = Path(project_root)
        
        # Load environment variables
        env_path = self.project_root / '.env'
        if env_path.exists():
            load_dotenv(env_path)
            logger.info(f"Loaded .env from: {env_path}")
        else:
            logger.warning(f".env file not found: {env_path}")
        
        # Load YAML configuration
        yaml_path = self.project_root / 'global_config.yaml'
        if yaml_path.exists():
            with open(yaml_path, 'r') as f:
                self.yaml_config = yaml.safe_load(f)
            logger.info(f"Loaded YAML config from: {yaml_path}")
        else:
            logger.warning(f"YAML config not found: {yaml_path}")
            self.yaml_config = {}
    
    def get_env(self, key: str, default: Any = None) -> Any:
        """
        Get environment variable
        
        Args:
            key: Environment variable name
            default: Default value if not found
            
        Returns:
            Environment variable value or default
        """
        return os.getenv(key, default)
    
    def get_yaml(self, *keys: str, default: Any = None) -> Any:
        """
        Get nested YAML configuration value
        
        Args:
            *keys: Nested keys (e.g., 'system', 'parallel_jobs')
            default: Default value if not found
            
        Returns:
            Configuration value or default
            
        Example:
            config.get_yaml('system', 'parallel_jobs')
            config.get_yaml('data', 'sources', 'polygon', 'enabled')
        """
        value = self.yaml_config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    # ========================================================================
    # CONVENIENCE METHODS FOR COMMON CONFIGURATIONS
    # ========================================================================
    
    @property
    def trading_mode(self) -> str:
        """Get trading mode (paper/live)"""
        return self.get_env('TRADING_MODE', 'paper')
    
    @property
    def is_paper_trading(self) -> bool:
        """Check if in paper trading mode"""
        return self.trading_mode.lower() == 'paper'
    
    @property
    def log_level(self) -> str:
        """Get log level"""
        return self.get_env('LOG_LEVEL', 'INFO')
    
    @property
    def log_dir(self) -> Path:
        """Get log directory"""
        log_dir = Path(self.get_env('LOG_DIR', self.project_root / 'logs'))
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir
    
    # Database configuration
    @property
    def database_url(self) -> str:
        """Get database connection URL"""
        return self.get_env('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/alphafactory')
    
    # API Keys
    @property
    def polygon_api_key(self) -> Optional[str]:
        """Get Polygon.io API key"""
        return self.get_env('POLYGON_API_KEY')
    
    @property
    def alpha_vantage_api_key(self) -> Optional[str]:
        """Get Alpha Vantage API key"""
        return self.get_env('ALPHAVANTAGE_API_KEY')
    
    @property
    def fmp_api_key(self) -> Optional[str]:
        """Get Financial Modeling Prep API key"""
        return self.get_env('FMP_API_KEY')
    
    # Interactive Brokers
    @property
    def ib_host(self) -> str:
        """Get IB host (paper or live based on trading mode)"""
        if self.is_paper_trading:
            return self.get_env('IB_PAPER_HOST', '127.0.0.1')
        return self.get_env('IB_LIVE_HOST', '127.0.0.1')
    
    @property
    def ib_port(self) -> int:
        """Get IB port (paper or live based on trading mode)"""
        if self.is_paper_trading:
            return int(self.get_env('IB_PAPER_PORT', '7497'))
        return int(self.get_env('IB_LIVE_PORT', '7496'))
    
    @property
    def ib_client_id(self) -> int:
        """Get IB client ID"""
        if self.is_paper_trading:
            return int(self.get_env('IB_PAPER_CLIENT_ID', '1'))
        return int(self.get_env('IB_LIVE_CLIENT_ID', '2'))
    
    # Backtest configuration
    @property
    def backtest_initial_capital(self) -> float:
        """Get backtest initial capital"""
        return float(self.get_env('BACKTEST_INITIAL_CAPITAL', '100000'))
    
    @property
    def backtest_commission_per_share(self) -> float:
        """Get backtest commission per share"""
        return float(self.get_env('BACKTEST_COMMISSION_PER_SHARE', '0.005'))
    
    @property
    def backtest_slippage_pct(self) -> float:
        """Get backtest slippage percentage"""
        return float(self.get_env('BACKTEST_SLIPPAGE_PCT', '0.05'))
    
    # System configuration from YAML
    @property
    def parallel_jobs(self) -> int:
        """Get number of parallel jobs"""
        return self.get_yaml('system', 'parallel_jobs', default=24)
    
    @property
    def data_dir(self) -> Path:
        """Get data directory"""
        data_dir = Path(self.get_yaml('system', 'data_dir', default=self.project_root / 'data'))
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir
    
    @property
    def results_dir(self) -> Path:
        """Get results directory"""
        results_dir = Path(self.get_yaml('system', 'results_dir', default=self.project_root / 'results'))
        results_dir.mkdir(parents=True, exist_ok=True)
        return results_dir
    
    def __repr__(self) -> str:
        """String representation"""
        return f"ConfigLoader(project_root='{self.project_root}', trading_mode='{self.trading_mode}')"


# Global configuration instance
config = ConfigLoader()


if __name__ == '__main__':
    """Test configuration loader"""
    from loguru import logger
    
    logger.info(f"Configuration loaded: {config}")
    logger.info(f"Trading mode: {config.trading_mode}")
    logger.info(f"Paper trading: {config.is_paper_trading}")
    logger.info(f"Log directory: {config.log_dir}")
    logger.info(f"Data directory: {config.data_dir}")
    logger.info(f"Polygon API key: {'*' * 10 if config.polygon_api_key else 'Not set'}")
    logger.info(f"Parallel jobs: {config.parallel_jobs}")
    logger.success("✓ Configuration loader working!")