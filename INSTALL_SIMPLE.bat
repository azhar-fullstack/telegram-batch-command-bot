@echo off
setlocal EnableExtensions
title Telegram Sender - Simple Install (no .venv)
cd /d "%~dp0"

echo.
echo ========================================
echo   Simple Install - no .venv folder
echo   Best for another PC / avoids path issues
echo ========================================
echo.

set "PY="

where python >nul 2>&1
if not errorlevel 1 set "PY=python"

if not defined PY (
    where py >nul 2>&1
    if not errorlevel 1 set "PY=py -3"
)

if not defined PY (
    echo [FAILED] Python was not found.
    echo Install Python and check "Add Python to PATH".
    pause
    exit /b 1
)

echo Using:
%PY% --version
echo.

echo Installing packages for this user...
%PY% -m pip install --upgrade pip
%PY% -m pip install -r requirements.txt
if errorlevel 1 (
    echo [FAILED] pip install failed.
    pause
    exit /b 1
)

echo Verifying app...
%PY% -c "import telegram_sender; print('OK')"
if errorlevel 1 (
    echo [FAILED] App check failed.
    pause
    exit /b 1
)

echo.
echo ========================================
echo   INSTALL COMPLETE
echo ========================================
echo.
echo Next step: double-click RUN_SIMPLE.bat
echo.
pause
exit /b 0
