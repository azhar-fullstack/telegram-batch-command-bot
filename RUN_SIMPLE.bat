@echo off
setlocal EnableExtensions
title Telegram Sender
cd /d "%~dp0"

set "PY="
where python >nul 2>&1
if not errorlevel 1 set "PY=python"
if not defined PY (
    where py >nul 2>&1
    if not errorlevel 1 set "PY=py -3"
)

if not defined PY (
    echo Python not found. Run INSTALL_SIMPLE.bat first.
    pause
    exit /b 1
)

echo Starting app...
start "" %PY% telegram_sender.py
