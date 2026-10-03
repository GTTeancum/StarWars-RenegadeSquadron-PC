@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Play-RenegadeSquadronPC.ps1" -Renderer DirectX12 %*
exit /b %errorlevel%
