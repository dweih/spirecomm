# Example AI executable
add_executable(simple_ai simple_ai.cpp)

target_link_libraries(simple_ai PRIVATE spirecomm)

# Set output directory for easier access
set_target_properties(simple_ai PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin
)

# On Windows, copy to specific config directories
if(WIN32)
    set_target_properties(simple_ai PROPERTIES
        RUNTIME_OUTPUT_DIRECTORY_DEBUG ${CMAKE_BINARY_DIR}/bin/Debug
        RUNTIME_OUTPUT_DIRECTORY_RELEASE ${CMAKE_BINARY_DIR}/bin/Release
    )
endif()
