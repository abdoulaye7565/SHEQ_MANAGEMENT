@echo off
cd /d "%~dp0"
powershell.exe -ExecutionPolicy Bypass -File "%~dp0preparer_flutter_android_flet.ps1"
pause
