# Native Vulkan backend dependencies, shared by game and asset-free renderer tests.
find_path(RENEGADE_VULKAN_HEADERS vulkan/vulkan.h HINTS "$ENV{VULKAN_SDK}/Include" "${PROJECT_SOURCE_DIR}/../../../.local/Vulkan-Headers/include" REQUIRED)
find_program(RENEGADE_DXC dxc HINTS "$ENV{VULKAN_SDK}/Bin" "${PROJECT_SOURCE_DIR}/../../../.local/dxc/bin/x64" REQUIRED)
find_package(Python3 3.10 COMPONENTS Interpreter REQUIRED)
set(RENEGADE_GPU_HOST "${PROJECT_SOURCE_DIR}/profiles/vcs/host")
set(RENEGADE_VULKAN_GENERATED "${CMAKE_BINARY_DIR}/vulkan-generated")
set(RENEGADE_VULKAN_SPIRV "${RENEGADE_VULKAN_GENERATED}/ge_vulkan_spirv.hpp")
add_custom_command(OUTPUT "${RENEGADE_VULKAN_SPIRV}"
 COMMAND "${Python3_EXECUTABLE}" "${PROJECT_SOURCE_DIR}/tools/compile_vulkan_shaders.py"
 "${RENEGADE_DXC}" "${RENEGADE_GPU_HOST}/ge_vulkan.hlsl" "${RENEGADE_VULKAN_SPIRV}"
 DEPENDS "${RENEGADE_GPU_HOST}/ge_vulkan.hlsl" "${PROJECT_SOURCE_DIR}/tools/compile_vulkan_shaders.py" VERBATIM)
# Own the output in this directory; explicit dependencies make it available
# before consumers in other directories start compiling.
add_custom_target(renegade_vulkan_shaders DEPENDS "${RENEGADE_VULKAN_SPIRV}")
set(RENEGADE_VULKAN_SOURCES "${RENEGADE_GPU_HOST}/ge_gpu_backend_vulkan.cpp" "${RENEGADE_GPU_HOST}/ge_gpu_backend_dispatch.cpp")

