cmake_minimum_required(VERSION 3.14)
project(spirecomm_cpp VERSION 1.0.0 LANGUAGES CXX)

# C++17 required
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# FetchContent for downloading dependencies
include(FetchContent)

# cpp-httplib (header-only HTTP client)
FetchContent_Declare(
    httplib
    GIT_REPOSITORY https://github.com/yhirose/cpp-httplib.git
    GIT_TAG        v0.14.3
)
FetchContent_MakeAvailable(httplib)

# nlohmann/json (header-only JSON library)
FetchContent_Declare(
    json
    GIT_REPOSITORY https://github.com/nlohmann/json.git
    GIT_TAG        v3.11.3
)
FetchContent_MakeAvailable(json)

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

# Platform-specific libraries
if(WIN32)
    # Windows requires Winsock libraries
    target_link_libraries(spirecomm PUBLIC ws2_32 crypt32)
endif()

# Enable warnings
if(MSVC)
    target_compile_options(spirecomm PRIVATE /W4)
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
