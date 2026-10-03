@echo off
call "%~dp0build-windows.cmd" --target RenegadeNative renegade_dx12_override_tests renegade_override_texture_tests renegade_override_msh_tests renegade_override_render_tests renegade_override_fog_tests renegade_override_skin_tests renegade_override_command_tests renegade_override_pose_tests renegade_override_model_tests renegade_display_tests renegade_stencil_tests
if errorlevel 1 exit /b %errorlevel%
set "PATH=%~dp0windows-sdk\bin;%PATH%"
"%~dp0build-tools\cmake\data\bin\ctest.exe" --test-dir "%~dp0build-windows-native" -R "renegade_(override_|dx12_override_tests|display_tests|stencil_tests)" --output-on-failure --timeout 60
exit /b %errorlevel%
