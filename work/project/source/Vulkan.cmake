# Native Vulkan backend dependencies, shared by game and asset-free renderer tests.
find_path(RENEGADE_VULKAN_HEADERS vulkan/vulkan.h HINTS "$ENV{VULKAN_SDK}/Include" "${PROJECT_SOURCE_DIR}/../../../.local/Vulkan-Headers/include" REQUIRED)
find_program(RENEGADE_DXC dxc HINTS "$ENV{VULKAN_SDK}/Bin" "${PROJECT_SOURCE_DIR}/../../../.local/dxc/bin/x64" REQUIRED)
find_package(Python3 3.10 COMPONENTS Interpreter REQUIRED)
set(RENEGADE_GPU_HOST "${PROJECT_SOURCE_DIR}/profiles/vcs/host")
set(RENEGADE_VULKAN_GENERATED "${CMAKE_BINARY_DIR}/vulkan-generated")
add_custom_command(OUTPUT "${RENEGADE_VULKAN_GENERATED}/ge_vulkan_spirv.hpp"
 COMMAND "${Python3_EXECUTABLE}" "${PROJECT_SOURCE_DIR}/tools/compile_vulkan_shaders.py"
 "${RENEGADE_DXC}" "${RENEGADE_GPU_HOST}/ge_vulkan.hlsl" "${RENEGADE_VULKAN_GENERATED}/ge_vulkan_spirv.hpp"
 DEPENDS "${RENEGADE_GPU_HOST}/ge_vulkan.hlsl" "${PROJECT_SOURCE_DIR}/tools/compile_vulkan_shaders.py" VERBATIM)
set(RENEGADE_VULKAN_SOURCES "${RENEGADE_GPU_HOST}/ge_gpu_backend_vulkan.cpp" "${RENEGADE_GPU_HOST}/ge_gpu_backend_dispatch.cpp" "${RENEGADE_VULKAN_GENERATED}/ge_vulkan_spirv.hpp")

