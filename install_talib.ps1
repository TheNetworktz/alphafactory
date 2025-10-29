# AlphaFactory OS - TA-Lib Installation Script for Windows
# This script downloads and installs the pre-compiled TA-Lib binary

Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "TA-Lib Windows Installation Script" -ForegroundColor Cyan
Write-Host "============================================`n" -ForegroundColor Cyan

# Detect Python version and architecture
$pythonVersion = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$pythonArch = python -c "import platform; print(platform.architecture()[0])"

Write-Host "Detected Python: $pythonVersion ($pythonArch)" -ForegroundColor Green

# Determine correct wheel file
if ($pythonArch -eq "64bit") {
    if ($pythonVersion -eq "3.10") {
        $wheelFile = "TA_Lib-0.4.28-cp310-cp310-win_amd64.whl"
        $wheelUrl = "https://github.com/cgohlke/talib-build/releases/download/v0.4.28/TA_Lib-0.4.28-cp310-cp310-win_amd64.whl"
    }
    elseif ($pythonVersion -eq "3.11") {
        $wheelFile = "TA_Lib-0.4.28-cp311-cp311-win_amd64.whl"
        $wheelUrl = "https://github.com/cgohlke/talib-build/releases/download/v0.4.28/TA_Lib-0.4.28-cp311-cp311-win_amd64.whl"
    }
    else {
        Write-Host "ERROR: Unsupported Python version $pythonVersion" -ForegroundColor Red
        Write-Host "Please use Python 3.10 or 3.11" -ForegroundColor Yellow
        exit 1
    }
}
else {
    Write-Host "ERROR: 32-bit Python detected. Please install 64-bit Python." -ForegroundColor Red
    exit 1
}

Write-Host "`nDownloading TA-Lib wheel: $wheelFile" -ForegroundColor Yellow

# Download wheel file
try {
    Invoke-WebRequest -Uri $wheelUrl -OutFile $wheelFile -UseBasicParsing
    Write-Host "Download complete!" -ForegroundColor Green
}
catch {
    Write-Host "ERROR: Failed to download TA-Lib wheel" -ForegroundColor Red
    Write-Host "Manual download: $wheelUrl" -ForegroundColor Yellow
    exit 1
}

# Install wheel
Write-Host "`nInstalling TA-Lib..." -ForegroundColor Yellow
try {
    python -m pip install $wheelFile
    Write-Host "TA-Lib installed successfully!" -ForegroundColor Green
}
catch {
    Write-Host "ERROR: Failed to install TA-Lib" -ForegroundColor Red
    exit 1
}

# Clean up
Remove-Item $wheelFile
Write-Host "`nCleaned up temporary files" -ForegroundColor Green

# Verify installation
Write-Host "`nVerifying TA-Lib installation..." -ForegroundColor Yellow
python -c "import talib; print(f'TA-Lib version: {talib.__version__}')"

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✓ TA-Lib installation SUCCESSFUL!`n" -ForegroundColor Green
}
else {
    Write-Host "`n✗ TA-Lib verification FAILED`n" -ForegroundColor Red
    exit 1
}