"""
AlphaFactory OS - Connection Test Script
Tests all database and API connections
"""

import os
import sys
from dotenv import load_dotenv
from colorama import Fore, Style, init

init(autoreset=True)

def print_header(text):
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}{text}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

def print_success(text):
    print(f"{Fore.GREEN}✓ {text}{Style.RESET_ALL}")

def print_error(text):
    print(f"{Fore.RED}✗ {text}{Style.RESET_ALL}")

def print_warning(text):
    print(f"{Fore.YELLOW}⚠ {text}{Style.RESET_ALL}")

def print_info(text):
    print(f"{Fore.BLUE}→ {text}{Style.RESET_ALL}")

def test_env_file():
    """Test if .env file exists and loads"""
    print_header("Test 1: Environment File")
    
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    
    if not os.path.exists(env_path):
        print_error(".env file not found")
        print_info(f"Expected location: {env_path}")
        return False
    
    print_success(f".env file found: {env_path}")
    
    load_dotenv(env_path)
    
    # Check critical variables
    critical_vars = [
        'DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD',
        'REDIS_HOST', 'REDIS_PORT',
        'LOG_DIR', 'TRADING_MODE'
    ]
    
    missing = []
    for var in critical_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print_error(f"Missing environment variables: {', '.join(missing)}")
        return False
    
    print_success("All critical environment variables present")
    return True

def test_postgresql():
    """Test PostgreSQL connection"""
    print_header("Test 2: PostgreSQL Database")
    
    try:
        import psycopg2
        print_success("psycopg2 library imported")
    except ImportError:
        print_error("psycopg2 not installed")
        return False
    
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
        print_success("Connected to PostgreSQL")
        
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print_info(f"PostgreSQL version: {version.split(',')[0]}")
        
        cursor.close()
        conn.close()
        print_success("PostgreSQL connection test passed")
        return True
        
    except Exception as e:
        print_error(f"PostgreSQL connection failed: {e}")
        print_info("Check DB_PASSWORD in .env matches PostgreSQL password")
        return False

def test_redis():
    """Test Redis connection"""
    print_header("Test 3: Redis Cache")
    
    try:
        import redis
        print_success("redis library imported")
    except ImportError:
        print_error("redis not installed")
        return False
    
    try:
        r = redis.Redis(
            host=os.getenv('REDIS_HOST'),
            port=int(os.getenv('REDIS_PORT')),
            db=int(os.getenv('REDIS_DB')),
            password=os.getenv('REDIS_PASSWORD') or None,
            decode_responses=True
        )
        
        # Test connection
        r.ping()
        print_success("Connected to Redis")
        
        # Test write/read
        r.set('test_key', 'test_value')
        value = r.get('test_key')
        r.delete('test_key')
        
        if value == 'test_value':
            print_success("Redis read/write test passed")
            return True
        else:
            print_error("Redis read/write test failed")
            return False
            
    except Exception as e:
        print_error(f"Redis connection failed: {e}")
        print_info("Check if Redis service is running")
        return False

def test_alpha_vantage():
    """Test Alpha Vantage API"""
    print_header("Test 4: Alpha Vantage API")
    
    api_key = os.getenv('ALPHAVANTAGE_API_KEY')
    
    if not api_key or api_key == 'your_alphavantage_api_key_here':
        print_warning("Alpha Vantage API key not set")
        print_info("Get free key: https://www.alphavantage.co/support/#api-key")
        return False
    
    try:
        import requests
        print_success("requests library imported")
        
        url = f'https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=IBM&interval=5min&apikey={api_key}'
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'Error Message' in data:
                print_error("Invalid API key")
                return False
            elif 'Note' in data:
                print_warning("API rate limit reached")
                print_info("Free tier: 5 calls/minute")
                return True
            else:
                print_success("Alpha Vantage API key valid")
                return True
        else:
            print_error(f"API request failed: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Alpha Vantage test failed: {e}")
        return False

def test_polygon():
    """Test Polygon API"""
    print_header("Test 5: Polygon.io API (Optional)")
    
    api_key = os.getenv('POLYGON_API_KEY')
    
    if not api_key or api_key == 'your_polygon_api_key_here':
        print_warning("Polygon API key not set")
        print_info("Optional: Get free key at https://polygon.io/dashboard/signup")
        print_info("Can skip for now, use later for real-time data")
        return None  # Not an error, just optional
    
    try:
        import requests
        
        url = f'https://api.polygon.io/v2/aggs/ticker/AAPL/prev?apiKey={api_key}'
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            print_success("Polygon API key valid")
            return True
        else:
            print_error(f"Polygon API test failed: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Polygon test failed: {e}")
        return False

def test_yfinance():
    """Test Yahoo Finance"""
    print_header("Test 6: Yahoo Finance (Free Data)")
    
    try:
        import yfinance as yf
        print_success("yfinance library imported")
        
        # Test data download
        ticker = yf.Ticker("AAPL")
        info = ticker.info
        
        if 'symbol' in info:
            print_success(f"Yahoo Finance working: {info.get('shortName', 'AAPL')}")
            return True
        else:
            print_error("Yahoo Finance data unavailable")
            return False
            
    except Exception as e:
        print_error(f"Yahoo Finance test failed: {e}")
        return False

def test_directories():
    """Test required directories exist"""
    print_header("Test 7: Project Directories")
    
    dirs = [
        os.getenv('LOG_DIR'),
        os.path.join(os.getenv('PYTHONPATH'), 'data'),
        os.path.join(os.getenv('PYTHONPATH'), 'models'),
        os.path.join(os.getenv('PYTHONPATH'), 'results'),
        os.path.join(os.getenv('PYTHONPATH'), 'backtests'),
    ]
    
    all_exist = True
    for directory in dirs:
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            print_info(f"Created: {directory}")
        elif directory:
            print_success(f"Exists: {directory}")
    
    return True

def main():
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}AlphaFactory OS - Connection Test Suite")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
    
    results = {
        'Environment File': test_env_file(),
        'PostgreSQL': test_postgresql(),
        'Redis': test_redis(),
        'Alpha Vantage': test_alpha_vantage(),
        'Polygon.io': test_polygon(),  # Can be None (optional)
        'Yahoo Finance': test_yfinance(),
        'Directories': test_directories(),
    }
    
    # Summary
    print_header("Test Summary")
    
    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)
    total = len([v for v in results.values() if v is not None])
    
    for test_name, result in results.items():
        if result is True:
            print_success(f"{test_name}")
        elif result is False:
            print_error(f"{test_name}")
        else:
            print_warning(f"{test_name} (optional - skipped)")
    
    print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"Total Tests: {total}")
    print(f"{Fore.GREEN}Passed: {passed}{Style.RESET_ALL}")
    if failed > 0:
        print(f"{Fore.RED}Failed: {failed}{Style.RESET_ALL}")
    if skipped > 0:
        print(f"{Fore.YELLOW}Skipped: {skipped} (optional){Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
    
    if failed == 0:
        print(f"{Fore.GREEN}✓ ALL REQUIRED TESTS PASSED!{Style.RESET_ALL}")
        print(f"{Fore.GREEN}✓ AlphaFactory OS is ready to run!{Style.RESET_ALL}\n")
        print(f"{Fore.YELLOW}Next: Reply 'next' for final setup steps{Style.RESET_ALL}\n")
        return 0
    else:
        print(f"{Fore.RED}✗ SOME TESTS FAILED{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Review errors above and fix issues{Style.RESET_ALL}\n")
        return 1

if __name__ == '__main__':
    sys.exit(main())