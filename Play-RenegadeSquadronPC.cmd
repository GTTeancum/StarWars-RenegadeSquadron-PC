@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Play-RenegadeSquadronPC.ps1" %*
exit /b %ERRORLEVEL%
