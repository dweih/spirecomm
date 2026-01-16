cmake_minimum_required(VERSION 3.14)
project(spirecomm_cpp VERSION 1.0.0 LANGUAGES CXX)

# Match parent project C++ standard (C++20)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Debug symbols configuration
if(CMAKE_BUILD_TYPE STREQUAL "Debug" OR NOT CMAKE_BUILD_TYPE)
    if(MSVC)
        # MSVC: Use /Zi for debug info, /Od for no optimization
        set(CMAKE_CXX_FLAGS_DEBUG "/Zi /Od")
    else()
        # GCC/Clang: Use -g for debug info, -O0 for no optimization
        set(CMAKE_CXX_FLAGS_DEBUG "-g -O0")
        set(CMAKE_C_FLAGS_DEBUG "-g -O0")
    endif()
endif()

# FetchContent for downloading dependencies
include(FetchContent)

# Only fetch dependencies if they haven't been fetched by parent project
# This prevents duplicate fetches and Git conflicts when building as a subproject

# cpp-httplib (header-only HTTP client)
if(NOT TARGET httplib::httplib)
    FetchContent_Declare(
        httplib
        GIT_REPOSITORY https://github.com/yhirose/cpp-httplib.git
        GIT_TAG        v0.14.3
    )
    
    # Disable HTTPS support for MSVC to avoid OpenSSL dependency
    if(MSVC)
        set(HTTPLIB_REQUIRE_OPENSSL OFF CACHE BOOL "Disable OpenSSL" FORCE)
        set(HTTPLIB_REQUIRE_ZLIB OFF CACHE BOOL "Disable zlib" FORCE)
        set(HTTPLIB_REQUIRE_BROTLI OFF CACHE BOOL "Disable Brotli" FORCE)
    endif()
    
    FetchContent_MakeAvailable(httplib)
    message(STATUS "SpireComm: Fetched cpp-httplib")
else()
    message(STATUS "SpireComm: Using cpp-httplib from parent project")
endif()

# nlohmann/json (header-only JSON library)
if(NOT TARGET nlohmann_json::nlohmann_json)
    FetchContent_Declare(
        json
        GIT_REPOSITORY https://github.com/nlohmann/json.git
        GIT_TAG        v3.11.3
    )
    FetchContent_MakeAvailable(json)
    message(STATUS "SpireComm: Fetched nlohmann/json")
else()
    message(STATUS "SpireComm: Using nlohmann/json from parent project")
endif()

# SpireComm client library
add_library(spirecomm STATIC
    src/client.cpp
)

target_include_directories(spirecomm PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)

target_link_libraries(spirecomm PUBLIC
    httplib::httplib
    nlohmann_json::nlohmann_json
)

# Platform-specific libraries and configuration
if(WIN32)
    # Windows requires Winsock libraries
    target_link_libraries(spirecomm PUBLIC ws2_32 crypt32)
    
    # For MSVC: We intentionally do NOT define CPPHTTPLIB_OPENSSL_SUPPORT
    # because httplib uses #ifdef (not #if), so defining it to 0 still enables it!
    if(MSVC)
        target_compile_definitions(spirecomm PRIVATE
            WIN32_LEAN_AND_MEAN
            NOMINMAX
            _CRT_SECURE_NO_WARNINGS
        )
        
        message(STATUS "SpireComm: Building without HTTPS support on MSVC (HTTP only)")
        message(STATUS "SpireComm: Using C++${CMAKE_CXX_STANDARD} to match parent project")
    endif()
endif()

# Enable warnings matching parent project style
if(MSVC)
    target_compile_options(spirecomm PRIVATE /W4)
    # Disable treating warnings as errors for spirecomm to avoid issues with example code
    target_compile_options(spirecomm PRIVATE /WX-)
else()
    target_compile_options(spirecomm PRIVATE -Wall -Wextra -Wpedantic)
endif()

# Examples subdirectory
add_subdirectory(examples)

# Installation rules (optional)
install(TARGETS spirecomm
    ARCHIVE DESTINATION lib
    LIBRARY DESTINATION lib
    RUNTIME DESTINATION bin
)

install(DIRECTORY include/
    DESTINATION include
)
