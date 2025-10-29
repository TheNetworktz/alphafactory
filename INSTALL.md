# AlphaFactory OS - Installation Guide

**Version:** 1.0  
**Date:** 2025-10-27  
**Hardware:** AMD Threadripper PRO 5975WX (32-core) + 256GB RAM  
**Estimated Time:** 15-20 minutes

---

## Prerequisites Checklist

Before proceeding, ensure you have:

- [x] Python 3.10 or 3.11 (64-bit) installed
- [x] Git installed (optional but recommended)
- [x] VS Code or text editor
- [x] Administrator access (for pip installations)
- [x] Stable internet connection (downloading ~500MB of packages)

---

## Step-by-Step Installation

### Step 1: Verify Python Installation
```powershell
# Open PowerShell in VS Code (Ctrl+`)
python --version
# Should show: Python 3.10.x or 3.11.x (64-bit)

# Verify pip
python -m pip --version
```

**Expected Output:**
```
Python 3.11.5
pip 23.3.1 from C:\Users\...\site-packages\pip (python 3.11)
```

---

### Step 2: Upgrade pip (Important)
```powershell
# Upgrade pip to latest version
python -m pip install --upgrade pip setuptools wheel

# Expected: pip upgraded to 23.3+
```

---

### Step 3: Install TA-Lib (CRITICAL - Do This First)

**TA-Lib requires special handling on Windows.**
```powershell
# Navigate to project directory
cd D:\AI_PROJECTS\alphafactory

# Run the TA-Lib installation script
powershell -ExecutionPolicy Bypass -File install_talib.ps1
```

**Expected Output:**
```
============================================
TA-Lib Windows Installation Script
============================================

Detected Python: 3.11 (64bit)

Downloading TA-Lib wheel: TA_Lib-0.4.28-cp311-cp311-win_amd64.whl
Download complete!

Installing TA-Lib...
TA-Lib installed successfully!

✓ TA-Lib installation SUCCESSFUL!
```

**If Script Fails (Manual Installation):**

1. Go to: https://github.com/cgohlke/talib-build/releases
2. Download the appropriate `.whl` file:
   - Python 3.10: `TA_Lib-0.4.28-cp310-cp310-win_amd64.whl`
   - Python 3.11: `TA_Lib-0.4.28-cp311-cp311-win_amd64.whl`
3. Install manually:
```powershell
   python -m pip install TA_Lib-0.4.28-cp311-cp311-win_amd64.whl
```

---

### Step 4: Install Core Dependencies
```powershell
# Install all packages from requirements.txt
python -m pip install -r requirements.txt

# This will take 5-10 minutes (downloading ~500MB)
# Your 32-core CPU will parallelize some compilations (XGBoost, LightGBM)
```

**Expected Output:**
```
Collecting pandas==2.1.3
  Downloading pandas-2.1.3-cp311-cp311-win_amd64.whl (11.0 MB)
Collecting numpy==1.26.2
  Downloading numpy-1.26.2-cp311-cp311-win_amd64.whl (15.8 MB)
...
Successfully installed pandas-2.1.3 numpy-1.26.2 ...
```

**Progress Indicator:**
```
[████████████████████████--------] 67% (Installing xgboost...)
```

---

### Step 5: Install Financial Modeling Prep SDK

**FMP is not on PyPI, requires manual installation:**
```powershell
# Install FMP Python SDK
python -m pip install git+https://github.com/JerBouma/FinanceToolkit.git

# Alternative (if git fails):
python -m pip install financetoolkit
```

---

### Step 6: Verify Installation

**Create verification script:**

**Save as:** `verify_install.py`
```python
"""
AlphaFactory OS - Installation Verification Script
Tests all critical dependencies
"""

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
```

**Run verification:**
```powershell
python verify_install.py
```

**Expected Output:**
```
============================================================
AlphaFactory OS - Installation Verification
============================================================

✓ pandas                         OK
✓ numpy                          OK
✓ scipy                          OK
✓ vectorbt                       OK
✓ TA-Lib                         OK
✓ pandas-ta                      OK
✓ ib-insync                      OK
...
============================================================
Total Packages: 26
Passed: 26
============================================================

✓ ALL DEPENDENCIES INSTALLED SUCCESSFULLY!
```

---

## Troubleshooting Common Issues

### Issue 1: TA-Lib Installation Fails

**Error:** `error: Microsoft Visual C++ 14.0 or greater is required`

**Solution:**
- Don't compile from source (use wheel file)
- Follow Step 3 carefully (use pre-compiled binary)
- Or download manually from: https://github.com/cgohlke/talib-build/releases

---

### Issue 2: pip SSL Certificate Error

**Error:** `SSL: CERTIFICATE_VERIFY_FAILED`

**Solution:**
```powershell
# Temporary fix (not recommended for production)
python -m pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt
```

---

### Issue 3: Permission Denied

**Error:** `PermissionError: [WinError 5] Access is denied`

**Solution:**
```powershell
# Run PowerShell as Administrator
# Or install to user directory:
python -m pip install --user -r requirements.txt
```

---

### Issue 4: Out of Memory During Installation

**Error:** `MemoryError` (unlikely with 256GB RAM, but just in case)

**Solution:**
```powershell
# Install packages one at a time
python -m pip install pandas
python -m pip install numpy
# ... etc
```

---

## Installation Complete Checklist

- [ ] Python 3.10/3.11 verified
- [ ] pip upgraded to 23.3+
- [ ] TA-Lib installed successfully
- [ ] All requirements.txt packages installed
- [ ] FMP SDK installed
- [ ] Verification script passes 100%
- [ ] No red errors in verification output

---

## Next Steps

1. Reply with **"next"** to receive:
   - Configuration files (.env.example, global_config.yaml)
   - Broker setup instructions (Interactive Brokers API)
   - Git initialization
   - Final verification steps

2. **Estimated Time Remaining:** 10-15 minutes

---

## Support

If you encounter issues:
- Paste the full error message
- Include output of `python --version`
- Include output of `python -m pip list`

---

**Your Progress: 40% Complete (Week 1, Day 1)**