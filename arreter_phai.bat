@echo off
chcp 65001 >nul
title PH.AI - Arret de PH.AI
cd /d "%~dp0"

echo ===================================================
echo   Arret de l'ecoute vocale et de PH.AI...
echo ===================================================
echo.

powershell -Command "Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*wake_word_listener.py*' -or $_.CommandLine -like '*main.py*' } | Stop-Process -Force" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq PH.AI*" >nul 2>&1

echo [OK] L'ecoute vocale et PH.AI ont ete arretes avec succes.
echo.
pause