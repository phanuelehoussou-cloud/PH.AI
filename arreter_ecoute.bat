@echo off
title Arrêt de PH.AI et de l'écoute vocale
cd /d "%~dp0"

echo ===================================================
echo   Arrêt de l'écoute vocale PH.AI en arrière-plan...
echo ===================================================
echo.

wmic process where "commandline like '%%wake_word_listener.py%%'" call terminate >nul 2>&1
wmic process where "commandline like '%%main.py%%'" call terminate >nul 2>&1
taskkill /F /IM python.exe /FI "WINDOWTITLE eq PH.AI*" >nul 2>&1

echo ✅ L'écoute vocale et PH.AI ont été complètement arrêtés.
echo.
pause
