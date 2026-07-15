@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Telegram Sender
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo .venv not found. Run INSTALL.bat first.
    echo Or use RUN_SIMPLE.bat if you ran INSTALL_SIMPLE.bat.
    pause
    exit /b 1
)

if exist ".venv\pyvenv.cfg" (
    for /f "usebackq tokens=1,* delims==" %%a in (".venv\pyvenv.cfg") do (
        if /i "%%a"=="home" (
            set "H=%%b"
            set "H=!H: =!"
            if not exist "!H!\python.exe" (
                echo .venv points to another PC: !H!\python.exe
                echo Run REINSTALL.bat on this PC first.
                pause
                exit /b 1
            )
        )
    )
)

echo Starting Telegram Batch Command Sender...
".venv\Scripts\pythonw.exe" telegram_sender.py 2>run_error.log

if exist run_error.log (
    for %%A in (run_error.log) do if %%~zA gtr 0 (
        echo.
        echo App failed to start:
        type run_error.log
        echo.
        echo Try REINSTALL.bat or INSTALL_SIMPLE.bat + RUN_SIMPLE.bat
        pause
        exit /b 1
    )
)

exit /b 0
