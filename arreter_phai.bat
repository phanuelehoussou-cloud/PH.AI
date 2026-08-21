@echo off
title PH.AI - Arret de PH.AI
cd /d "%~dp0"

echo ===================================================
echo   Arret de l ecoute vocale et de PH.AI...
echo ===================================================
echo.

powershell -Command "$procs = Get-CimInstance Win32_Process | Where-Object { $null -ne $_.CommandLine -and ($_.CommandLine.Contains('wake_word_listener.py') -or $_.CommandLine.Contains('main.py')) }; foreach ($p in $procs) { Stop-Process -Id $p.ProcessId -Force }" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq PH.AI*" >nul 2>&1

echo [OK] L ecoute vocale et PH.AI ont ete arretes avec succes.
echo.
pause