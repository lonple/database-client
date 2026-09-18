@echo off
REM One-click wrapper: bypasses PowerShell execution policy
REM Usage (from repo root):
REM   scripts\docker-deploy.cmd
REM   scripts\docker-deploy.cmd -Build
REM   scripts\docker-deploy.cmd -Full
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0docker-deploy.ps1" %*
exit /b %ERRORLEVEL%
