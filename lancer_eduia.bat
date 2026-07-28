@echo off
title PH.AI - Toujours disponible for my LORD !
cd /d "%~dp0"
echo ===================================================
echo   Lancement de PH.AI (Toujours disponible for my LORD)...
echo ===================================================
echo.
if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe main.py
) else (
    python main.py
)
pause
