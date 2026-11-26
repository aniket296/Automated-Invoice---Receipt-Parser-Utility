@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0\.."

echo ============================================================================
echo   Automated Invoice ^& Receipt Parser Utility - Windows Installer Builder
echo ============================================================================

call "scripts\build_exe.bat"
if !ERRORLEVEL! NEQ 0 (
    echo [ERROR] Standalone .exe build failed. Cannot proceed with installer.
    exit /b 1
)

set "ISCC_PATH="

if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" (
    set "ISCC_PATH=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
) else if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" (
    set "ISCC_PATH=%ProgramFiles%\Inno Setup 6\ISCC.exe"
) else if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" (
    set "ISCC_PATH=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
) else (
    for /f "delims=" %%I in ('where ISCC.exe 2^>nul') do (
        set "ISCC_PATH=%%I"
    )
)

if defined ISCC_PATH (
    echo [Installer] Found Inno Setup Compiler: "!ISCC_PATH!"
    "!ISCC_PATH!" "installer\setup.iss"
    if !ERRORLEVEL! NEQ 0 (
        echo [ERROR] Inno Setup compilation failed.
        exit /b 1
    )
    echo ============================================================================
    echo [SUCCESS] Windows Setup Installer ready:
    echo   dist_installer\InvoiceReceiptParser_Setup.exe
    echo ============================================================================
    exit /b 0
) else (
    echo ============================================================================
    echo [NOTICE] Inno Setup 6 ^(ISCC.exe^) was not detected on this machine.
    echo   - Standalone executable is ready at: dist\InvoiceReceiptParser.exe
    echo   - To compile the full Windows Setup wizard ^(InvoiceReceiptParser_Setup.exe^),
    echo     install Inno Setup 6 from: https://jrsoftware.org/isdl.php
    echo     and re-run scripts\build_installer.bat.
    echo ============================================================================
    exit /b 0
)
