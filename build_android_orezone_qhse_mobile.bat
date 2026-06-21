@echo off
cd /d "%~dp0"
powershell.exe -ExecutionPolicy Bypass -File "%~dp0build_android_orezone_qhse_mobile.ps1"
pause
