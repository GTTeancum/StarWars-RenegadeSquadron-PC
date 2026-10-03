@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64
if errorlevel 1 exit /b %errorlevel%
set "PATH=C:\Program Files\Microsoft Visual Studio\18\Community\VC\Tools\MSVC\14.44.35207\bin\HostX64\x64;C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64;%PATH%"
set "INCLUDE=C:\Program Files\Microsoft Visual Studio\18\Community\VC\Tools\MSVC\14.44.35207\include;C:\Program Files (x86)\Windows Kits\10\Include\10.0.26100.0\ucrt;C:\Program Files (x86)\Windows Kits\10\Include\10.0.26100.0\shared;C:\Program Files (x86)\Windows Kits\10\Include\10.0.26100.0\um"
set "LIB=C:\Program Files\Microsoft Visual Studio\18\Community\VC\Tools\MSVC\14.44.35207\lib\x64;C:\Program Files (x86)\Windows Kits\10\Lib\10.0.26100.0\ucrt\x64;C:\Program Files (x86)\Windows Kits\10\Lib\10.0.26100.0\um\x64"
set "INCLUDE=%INCLUDE%;C:\Program Files (x86)\Windows Kits\10\Include\10.0.26100.0\winrt"
"%~dp0build-tools\cmake\data\bin\cmake.exe" -S "%~dp0project\source" -B "%~dp0build-windows-native" -G Ninja -DCMAKE_MAKE_PROGRAM="%~dp0build-tools\bin\ninja.exe" -DCMAKE_BUILD_TYPE=Release -DPSPRECOMP_PROFILE=renegade -DPSPRECOMP_MSVC_MP_JOBS=1 -DRENEGADE_SDK="%~dp0windows-sdk" -DCMAKE_LIBRARY_PATH="%~dp0windows-sdk\lib" -DRENEGADE_DISC_ROOT="%~dp0game\disc" %*
exit /b %errorlevel%
