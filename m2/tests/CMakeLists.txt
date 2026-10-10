cmake_minimum_required(VERSION 3.20)
project(EnhancedFrameClockTests LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
add_executable(M2FrameClockTest test_frame_clock.cpp)

add_executable(M2DebugTraceTest test_debug.cpp)

add_executable(M2PauseInterpolationTest test_pause.cpp)

add_executable(M2EscapePolicyTest test_escape.cpp)

add_executable(M2RenderCoordinatesTest test_render_coordinates.cpp)

add_executable(M2ObjectInterpolationTest test_object_interpolation.cpp)
