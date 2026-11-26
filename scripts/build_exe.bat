@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0\.."

echo ============================================================================
echo   Automated Invoice ^& Receipt Parser Utility - Standalone .EXE Builder
echo ============================================================================

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment .venv not found. Run run_local.bat first.
    exit /b 1
)

call ".venv\Scripts\activate.bat"

echo [1/3] Running automated unit test suite ^(pytest^)...
".venv\Scripts\pytest.exe"
if !ERRORLEVEL! NEQ 0 (
    echo [ERROR] Unit tests failed. Aborting .exe build.
    exit /b 1
)

echo [2/3] Generating multi-resolution icon ^(assets\app_icon.ico^)...
".venv\Scripts\python.exe" scripts\generate_icon.py
if !ERRORLEVEL! NEQ 0 (
    echo [ERROR] Icon generation failed.
    exit /b 1
)

echo [3/3] Building standalone executable with PyInstaller...
".venv\Scripts\pyinstaller.exe" --clean --noconfirm build_windows.spec
if !ERRORLEVEL! NEQ 0 (
    echo [ERROR] PyInstaller compilation failed.
    exit /b 1
)

if not exist "dist\InvoiceReceiptParser.exe" (
    echo [ERROR] Expected output dist\InvoiceReceiptParser.exe was not found.
    exit /b 1
)

echo ============================================================================
echo [SUCCESS] Standalone Windows executable built: dist\InvoiceReceiptParser.exe
echo ============================================================================
exit /b 0
