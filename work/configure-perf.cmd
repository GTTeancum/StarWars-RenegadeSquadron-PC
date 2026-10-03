@echo off
rem Performance build: same sources as configure-windows.cmd, Visual Studio 2022
rem toolchain on this machine, separate build directory work\build-perf.
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b %errorlevel%
set "CMAKE=cmake"
if exist "%~dp0build-tools\cmake\data\bin\cmake.exe" set "CMAKE=%~dp0build-tools\cmake\data\bin\cmake.exe"
set "NINJA=ninja"
if exist "%~dp0build-tools\bin\ninja.exe" set "NINJA=%~dp0build-tools\bin\ninja.exe"
"%CMAKE%" -S "%~dp0project\source" -B "%~dp0build-perf" -G Ninja -DCMAKE_MAKE_PROGRAM="%NINJA%" -DCMAKE_BUILD_TYPE=Release -DPSPRECOMP_PROFILE=renegade -DPSPRECOMP_MSVC_MP_JOBS=1 -DRENEGADE_SDK="%~dp0windows-sdk" -DCMAKE_LIBRARY_PATH="%~dp0windows-sdk\lib" -DRENEGADE_DISC_ROOT="%~dp0game\disc" %*
exit /b %errorlevel%
