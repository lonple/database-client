@echo off
REM One-click stop wrapper
REM Usage (from repo root):
REM   scripts\docker-stop.cmd
REM   scripts\docker-stop.cmd -WipeData
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0docker-stop.ps1" %*
exit /b %ERRORLEVEL%
