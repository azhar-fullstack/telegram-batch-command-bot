@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Telegram Sender - Install
cd /d "%~dp0"

echo.
echo ========================================
echo   Telegram Batch Command Sender
echo   One-time install
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
    echo.
    echo Install Python from https://www.python.org/downloads/
    echo Check "Add Python to PATH" during install, then run this again.
    echo.
    goto :fail
)

echo Found Python:
%PY% --version
echo.

echo [1/3] Creating virtual environment...
set "NEED_VENV=1"

if exist ".venv\Scripts\python.exe" (
    call :check_venv
    if !errorlevel! equ 0 (
        set "NEED_VENV=0"
        echo       .venv looks OK on this PC, reusing it.
    ) else (
        echo       .venv is from another PC or old location.
        echo       Deleting broken .venv...
        rmdir /s /q ".venv" 2>nul
    )
)

if "!NEED_VENV!"=="1" (
    %PY% -m venv .venv
    if errorlevel 1 (
        echo [FAILED] Could not create .venv
        goto :fail
    )
    echo       Created fresh .venv for this PC.
)

echo [2/3] Installing packages...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :venv_broken

".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :venv_broken

echo [3/3] Verifying app...
".venv\Scripts\python.exe" -c "import telegram_sender; print('OK')"
if errorlevel 1 goto :venv_broken

echo.
echo ========================================
echo   INSTALL COMPLETE
echo ========================================
echo.
echo Next step: double-click RUN.bat
echo.
pause
exit /b 0

:check_venv
rem Returns 0 if venv works on THIS computer, 1 if broken/copied from elsewhere
if not exist ".venv\pyvenv.cfg" exit /b 1

for /f "usebackq tokens=1,* delims==" %%a in (".venv\pyvenv.cfg") do (
    set "KEY=%%a"
    set "VAL=%%b"
    set "KEY=!KEY: =!"
    if /i "!KEY!"=="home" set "VENV_HOME=!VAL: =!"
    if /i "!KEY!"=="executable" set "VENV_EXE=!VAL: =!"
)

if defined VENV_HOME (
    if not exist "!VENV_HOME!\python.exe" (
        echo       Found old path: !VENV_HOME!\python.exe
        exit /b 1
    )
)

if defined VENV_EXE (
    if not exist "!VENV_EXE!" (
        echo       Found old path: !VENV_EXE!
        exit /b 1
    )
)

".venv\Scripts\python.exe" -c "import telegram_sender" >nul 2>&1
if errorlevel 1 exit /b 1

exit /b 0

:venv_broken
echo.
echo [FAILED] The .venv on this PC is still broken.
echo.
echo Run REINSTALL.bat  OR  delete the .venv folder and run INSTALL.bat again.
echo.
echo If problems continue, use INSTALL_SIMPLE.bat instead (no .venv needed).
goto :fail

:fail
echo.
echo Install did NOT finish. Read the messages above.
echo.
echo IMPORTANT when copying to another PC:
echo   Do NOT copy the .venv folder inside the zip.
echo   On the new PC run INSTALL.bat or INSTALL_SIMPLE.bat once.
echo.
pause
exit /b 1
