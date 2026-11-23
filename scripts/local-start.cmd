@echo off
REM DBC local one-click start (bypass PowerShell execution policy)
REM Usage (repo root):
REM   scripts\local-start.cmd
REM   scripts\local-start.cmd askdata gateway front
REM   scripts\local-start.cmd -Background askdata gateway
REM   scripts\local-start.cmd -NoAskdataDebugger askdata
REM Short names: askdata audit gateway front manage sqlwork usercenter(uc)
REM No names = all (stop then start). Default = foreground merged logs.
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0local-start.ps1" %*
exit /b %ERRORLEVEL%
