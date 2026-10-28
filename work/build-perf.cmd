@echo off
if not exist "%~dp0..\.local\temp" mkdir "%~dp0..\.local\temp"
set "TEMP=%~dp0..\.local\temp"
set "TMP=%TEMP%"
rem Usage: build-perf.cmd [jobs] [ninja targets...]
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b %errorlevel%
set "CMAKE=cmake"
if exist "%~dp0build-tools\cmake\data\bin\cmake.exe" set "CMAKE=%~dp0build-tools\cmake\data\bin\cmake.exe"
set "NINJA=ninja"
if exist "C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja\ninja.exe" set "NINJA=C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja\ninja.exe"
if exist "%~dp0build-tools\bin\ninja.exe" set "NINJA=%~dp0build-tools\bin\ninja.exe"
set "ROOT=%~dp0"
set "JOBS=%~1"
if "%JOBS%"=="" set "JOBS=6"
shift
set "TARGETS="
:collect
if "%~1"=="" goto run
set "TARGETS=%TARGETS% %~1"
shift
goto collect
:run
"%NINJA%" -C "%ROOT%build-perf" -j %JOBS% %TARGETS%
exit /b %errorlevel%
