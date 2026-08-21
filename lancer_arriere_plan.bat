@echo off
cd /d "%~dp0"
if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" wake_word_listener.py
) else (
    python wake_word_listener.py
)
