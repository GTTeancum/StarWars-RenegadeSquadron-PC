@echo off
setlocal
cd /d "%~dp0.."
if not exist ".local\temp" mkdir ".local\temp"
set "TEMP=%CD%\.local\temp"
set "TMP=%TEMP%"
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
set "NINJA=C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja\ninja.exe"
cmake -S work/project/source -B .local/build-vulkan -G Ninja -DCMAKE_MAKE_PROGRAM="%NINJA%" -DCMAKE_BUILD_TYPE=Release -DPSPRECOMP_BUILD_TESTS=OFF -DPSPRECOMP_BUILD_VULKAN_TESTS=ON
if errorlevel 1 exit /b 1
cmake --build .local/build-vulkan --target renegade_vulkan_tests renegade_disc_setup_test --parallel 2
if errorlevel 1 exit /b 1
ctest --test-dir .local/build-vulkan -R renegade_vulkan_tests --output-on-failure --timeout 60
exit /b %errorlevel%
