@echo off
rem Generates the translated game code from your own ULUS10292 BOOT.BIN.
rem Usage: generate-perf.cmd [output-directory]
rem Default output: work\project\source\profiles\renegade\generated (not distributed).
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b %errorlevel%
set "ROOT=%~dp0"
set "OUT=%~1"
if "%OUT%"=="" set "OUT=%ROOT%project\source\profiles\renegade\generated"
set "CMAKE=cmake"
if exist "%ROOT%build-tools\cmake\data\bin\cmake.exe" set "CMAKE=%ROOT%build-tools\cmake\data\bin\cmake.exe"
set "NINJA=ninja"
if exist "%ROOT%build-tools\bin\ninja.exe" set "NINJA=%ROOT%build-tools\bin\ninja.exe"
set "BOOT=%ROOT%game\disc\PSP_GAME\SYSDIR\BOOT.BIN"
if not exist "%BOOT%" echo Missing %BOOT% - extract your game disc to work\game\disc first.& exit /b 1
rem The recompiler is part of the framework; build it without the game profile.
"%CMAKE%" -S "%ROOT%project\source" -B "%ROOT%build-framework" -G Ninja -DCMAKE_MAKE_PROGRAM="%NINJA%" -DCMAKE_BUILD_TYPE=Release -DPSPRECOMP_PROFILE= -DPSPRECOMP_BUILD_TESTS=OFF
if errorlevel 1 exit /b %errorlevel%
"%NINJA%" -C "%ROOT%build-framework" psp_recomp
if errorlevel 1 exit /b %errorlevel%
if not exist "%OUT%" mkdir "%OUT%"
"%ROOT%build-framework\psp_recomp.exe" "%BOOT%" --auto "%OUT%" 0x08804000 8192
exit /b %errorlevel%
