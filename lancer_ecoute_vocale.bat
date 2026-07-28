@echo off
title PH.AI - Service d'Activation Vocale (LET'S GO / ARISE)
cd /d "%~dp0"
echo ===================================================
echo   Activation de l'ecoute vocale PH.AI (LET'S GO)...
echo ===================================================
echo.
if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe wake_word_listener.py
) else (
    python wake_word_listener.py
)
pause
