@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Play-RenegadeSquadronPC.ps1" -OverridePack "work/mods-user" %*
exit /b %errorlevel%
