@echo off
cd /d "%~dp0"
powershell.exe -ExecutionPolicy Bypass -File "%~dp0preparer_android_orezone_qhse_mobile.ps1"
pause
