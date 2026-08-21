@echo off
title Installation de PH.AI au demarrage de Windows
cd /d "%~dp0"

echo ===================================================
echo   Installation de PH.AI au demarrage de Windows
echo ===================================================
echo.

set "SCRIPT_VBS=%~dp0lancer_arriere_plan.vbs"
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT=%STARTUP_FOLDER%\PH.AI_EcouteVocale.lnk"

powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut([System.Environment]::ExpandEnvironmentVariables('%%APPDATA%%\Microsoft\Windows\Start Menu\Programs\Startup\PH.AI_EcouteVocale.lnk')); $s.TargetPath = '%SCRIPT_VBS%'; $s.WorkingDirectory = '%~dp0'; $s.Save()"

if exist "%SHORTCUT%" (
    echo [OK] PH.AI est configure pour demarrer automatiquement avec Windows !
    echo.
    echo Lancement du service d ecoute vocale en arriere-plan...
    wscript "%SCRIPT_VBS%"
    echo [OK] Ecoute vocale active en arriere-plan. Dites LET S GO ou ARISE a tout moment !
) else (
    echo [ERREUR] Impossible de creer le raccourci au demarrage.
)

echo.
pause
