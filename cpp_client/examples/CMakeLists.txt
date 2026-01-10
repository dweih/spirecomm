# Example AI executables

add_executable(example_ai example_ai.cpp)
target_link_libraries(example_ai PRIVATE spirecomm)

# Set output directory
set_target_properties(example_ai PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin
)
