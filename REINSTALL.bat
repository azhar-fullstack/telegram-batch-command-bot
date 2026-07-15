@echo off
setlocal EnableExtensions
title Telegram Sender - Reinstall
cd /d "%~dp0"

echo.
echo This deletes the old .venv and installs fresh.
echo Use this after moving the folder or copying to another PC.
echo.
pause

if exist ".venv" (
    echo Deleting .venv ...
    rmdir /s /q ".venv"
)

call "%~dp0INSTALL.bat"
