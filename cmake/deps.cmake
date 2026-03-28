if(POLICY CMP0135)
    cmake_policy(SET CMP0135 NEW)
endif()

set(CMAKE_MODULE_PATH "${PROJECT_SOURCE_DIR}/cmake")

include(FetchContent)

message(STATUS "Fetching mrexodia/mbedtls v3.6.5-clang-windows-fix...")
FetchContent_Declare(
    mbedtls
    GIT_REPOSITORY https://github.com/mrexodia/mbedtls.git
    GIT_TAG v3.6.5-clang-windows-fix
    GIT_SHALLOW TRUE
)
set(ENABLE_TESTING OFF CACHE BOOL "" FORCE)
set(ENABLE_PROGRAMS OFF CACHE BOOL "" FORCE)
set(MBEDTLS_FATAL_WARNINGS OFF CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(mbedtls)

message(STATUS "Fetching yhirose/cpp-httplib v0.40.0...")
FetchContent_Declare(
    cpp-httplib
    GIT_REPOSITORY https://github.com/yhirose/cpp-httplib.git
    GIT_TAG v0.40.0
    GIT_SHALLOW TRUE
)
set(HTTPLIB_USE_OPENSSL_IF_AVAILABLE OFF CACHE BOOL "" FORCE)
set(HTTPLIB_REQUIRE_MBEDTLS ON CACHE BOOL "" FORCE)
set(HTTPLIB_INSTALL OFF CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(cpp-httplib)

message(STATUS "Fetching nlohmann/json v3.12.0...")
FetchContent_Declare(
    json URL https://github.com/nlohmann/json/releases/download/v3.12.0/json.tar.xz
    URL_HASH SHA256=42f6e95cad6ec532fd372391373363b62a14af6d771056dbfc86160e6dfff7aa
)
FetchContent_MakeAvailable(json)

message(STATUS "Fetching fmtlib/fmt v12.1.0...")
FetchContent_Declare(
    fmt
    URL https://github.com/fmtlib/fmt/releases/download/12.1.0/fmt-12.1.0.zip
    URL_HASH SHA256=695fd197fa5aff8fc67b5f2bbc110490a875cdf7a41686ac8512fb480fa8ada7
)
FetchContent_MakeAvailable(fmt)

message(STATUS "Fetching daandemeyer/reproc v14.2.5...")
FetchContent_Declare(
    repoc
    GIT_REPOSITORY https://github.com/daandemeyer/reproc.git
    GIT_TAG v14.2.5
    GIT_SHALLOW TRUE
)
FetchContent_MakeAvailable(repoc)
