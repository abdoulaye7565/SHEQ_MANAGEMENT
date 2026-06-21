@echo off
cd /d "%~dp0"
powershell.exe -ExecutionPolicy Bypass -File "%~dp0telecharger_jdk17_temurin.ps1"
pause
