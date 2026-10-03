@echo off
call "%~dp0configure-windows.cmd"
if errorlevel 1 exit /b %errorlevel%
python "%~dp0test-asset-hook-build030.py"
exit /b %errorlevel%
