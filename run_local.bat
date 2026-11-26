@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo ============================================================================
echo   Automated Invoice ^& Receipt Parser Utility - Local Source Launcher
echo ============================================================================

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creating local Python virtual environment ^(.venv^)...
    where py >nul 2>nul
    if !ERRORLEVEL! EQU 0 (
        py -3.12 -m venv .venv 2>nul || py -3.11 -m venv .venv 2>nul || python -m venv .venv
    ) else (
        python -m venv .venv
    )
    if not exist ".venv\Scripts\python.exe" (
        echo [ERROR] Failed to create .venv. Please ensure Python 3.11+ is installed.
        exit /b 1
    )
    echo [2/3] Installing runtime dependencies from requirements.txt...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if !ERRORLEVEL! NEQ 0 (
        echo [ERROR] Dependency installation failed.
        exit /b 1
    )
)

if not exist "assets\app_icon.ico" (
    echo [Icon] Generating multi-resolution application icon ^(assets\app_icon.ico^)...
    ".venv\Scripts\python.exe" scripts\generate_icon.py
)

echo [Launch] Starting Automated Invoice ^& Receipt Parser Utility...
".venv\Scripts\python.exe" -m src.main
exit /b %ERRORLEVEL%
