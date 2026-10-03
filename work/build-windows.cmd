@echo off
call "%~dp0configure-windows.cmd"
if errorlevel 1 exit /b %errorlevel%
"%~dp0build-tools\cmake\data\bin\cmake.exe" --build "%~dp0build-windows-native" --parallel 2 %*
exit /b %errorlevel%
