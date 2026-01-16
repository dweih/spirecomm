# Example AI executable
add_executable(simple_combat_ai simple_combat_ai.cpp)

target_link_libraries(simple_combat_ai PRIVATE spirecomm)

# Disable treating warnings as errors for examples
if(MSVC)
    target_compile_options(simple_combat_ai PRIVATE /WX-)
endif()

# Set output directory for easier access
set_target_properties(simple_combat_ai PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin
)

# On Windows, copy to specific config directories
if(WIN32)
    set_target_properties(simple_combat_ai PROPERTIES
        RUNTIME_OUTPUT_DIRECTORY_DEBUG ${CMAKE_BINARY_DIR}/bin/Debug
        RUNTIME_OUTPUT_DIRECTORY_RELEASE ${CMAKE_BINARY_DIR}/bin/Release
    )
endif()

# Full Game Test executable
add_executable(full_game_test full_game_test.cpp)

target_link_libraries(full_game_test PRIVATE spirecomm)

# Disable treating warnings as errors for examples
if(MSVC)
    target_compile_options(full_game_test PRIVATE /WX-)
endif()

# Set output directory for easier access
set_target_properties(full_game_test PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin
)

# On Windows, copy to specific config directories
if(WIN32)
    set_target_properties(full_game_test PROPERTIES
        RUNTIME_OUTPUT_DIRECTORY_DEBUG ${CMAKE_BINARY_DIR}/bin/Debug
        RUNTIME_OUTPUT_DIRECTORY_RELEASE ${CMAKE_BINARY_DIR}/bin/Release
    )
endif()
