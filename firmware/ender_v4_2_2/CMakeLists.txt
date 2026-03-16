cmake_minimum_required(VERSION 3.16)
project(tars_ender_firmware_reference CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_executable(firmware_reference_native
    src/main.cpp
    src/firmware_app.cpp
)

target_include_directories(firmware_reference_native PRIVATE include)
