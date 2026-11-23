@echo off
REM One-click wrapper: bypasses PowerShell execution policy
REM Usage (from repo root):
REM   scripts\docker-deploy.cmd
REM   scripts\docker-deploy.cmd -Build
REM   scripts\docker-deploy.cmd -Build askdata
REM   scripts\docker-deploy.cmd -Build sqlwork front
REM Short names: askdata sqlwork front gateway usercenter(uc) manage audit
REM   scripts\docker-deploy.cmd -Full
REM Starts middleware + Java apps + dbc-askdata + front (no raw docker compose needed).
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0docker-deploy.ps1" %*
exit /b %ERRORLEVEL%
