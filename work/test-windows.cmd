@echo off
set "PATH=%~dp0windows-sdk\bin;%PATH%"
"%~dp0build-tools\cmake\data\bin\ctest.exe" --test-dir "%~dp0build-windows-native" --output-on-failure --timeout 120 %*
exit /b %errorlevel%
