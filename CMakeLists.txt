cmake_minimum_required(VERSION 3.24...4.2.1)

project(agent)

if(CMAKE_SOURCE_DIR STREQUAL CMAKE_BINARY_DIR)
    message(FATAL_ERROR "In-tree builds are not supported. Run CMake from a separate directory: cmake -B build")
endif()

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

include(cmake/deps.cmake)

if(NOT EXISTS "${PROJECT_SOURCE_DIR}/.env")
    message(FATAL_ERROR "Missing .env file. Please create one based on .env.example")
endif()
file(TO_NATIVE_PATH "${PROJECT_SOURCE_DIR}/.env" DOTENV)

add_executable(agent
    src/cli.cpp
    src/utils.cpp
)
target_link_libraries(agent PRIVATE
    httplib::httplib
    nlohmann_json::nlohmann_json
    fmt::fmt
    args::args
    reproc
    $<$<PLATFORM_ID:Darwin>:$<LINK_LIBRARY:FRAMEWORK,Security>>
)
target_precompile_headers(agent PRIVATE
    <filesystem>
    <nlohmann/json.hpp>
    <fmt/format.h>
)
target_compile_features(agent PRIVATE cxx_std_17)
target_compile_definitions(agent PRIVATE DOTENV="${DOTENV}")