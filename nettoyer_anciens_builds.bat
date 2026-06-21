@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0nettoyer_anciens_builds.ps1" -Confirmer
pause
