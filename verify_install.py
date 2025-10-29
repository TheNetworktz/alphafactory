import sys
from colorama import Fore, Style, init

init(autoreset=True)

def check_package(package_name, import_name=None):
    """Test if a package can be imported"""
    if import_name is None:
        import_name = package_name
    
    try:
        __import__(import_name)
        print(f"{Fore.GREEN}✓ {package_name:30} OK{Style.RESET_ALL}")
        return True
    except ImportError as e:
        print(f"{Fore.RED}✗ {package_name:30} FAILED: {e}{Style.RESET_ALL}")
        return False

def main():
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}AlphaFactory OS - Installation Verification")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
    
    packages = [
        # Core
        ('pandas', 'pandas'),
        ('numpy', 'numpy'),
        ('scipy', 'scipy'),
        
        # Backtesting
        ('vectorbt', 'vectorbt'),
        
        # Technical Analysis
        ('TA-Lib', 'talib'),
        ('pandas-ta', 'pandas_ta'),
        
        # Broker
        ('ib-insync', 'ib_insync'),
        
        # Data
        ('polygon', 'polygon'),
        ('yfinance', 'yfinance'),
        
        # Database
        ('sqlalchemy', 'sqlalchemy'),
        ('psycopg2', 'psycopg2'),
        ('redis', 'redis'),
        
        # ML
        ('scikit-learn', 'sklearn'),
        ('xgboost', 'xgboost'),
        ('lightgbm', 'lightgbm'),
        
        # Visualization
        ('dash', 'dash'),
        ('plotly', 'plotly'),
        
        # Alerts
        ('telegram', 'telegram'),
        
        # Config
        ('yaml', 'yaml'),
        ('dotenv', 'dotenv'),
        ('loguru', 'loguru'),
        
        # Testing
        ('pytest', 'pytest'),
        
        # Optimization
        ('numba', 'numba'),
        ('joblib', 'joblib'),
    ]
    
    results = []
    for package_name, import_name in packages:
        results.append(check_package(package_name, import_name))
    
    # Summary
    total = len(results)
    passed = sum(results)
    failed = total - passed
    
    print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"Total Packages: {total}")
    print(f"{Fore.GREEN}Passed: {passed}{Style.RESET_ALL}")
    if failed > 0:
        print(f"{Fore.RED}Failed: {failed}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
    
    if failed == 0:
        print(f"{Fore.GREEN}✓ ALL DEPENDENCIES INSTALLED SUCCESSFULLY!{Style.RESET_ALL}\n")
        print(f"{Fore.YELLOW}Next: Reply with 'next' to receive configuration files{Style.RESET_ALL}\n")
        return 0
    else:
        print(f"{Fore.RED}✗ SOME DEPENDENCIES FAILED{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Please review errors above and reinstall failed packages{Style.RESET_ALL}\n")
        return 1

if __name__ == '__main__':
    sys.exit(main())