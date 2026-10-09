cmake_minimum_required(VERSION 3.20)
project(EnhancedFrameClockTests LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
add_executable(M2FrameClockTest test_frame_clock.cpp)

add_executable(M2DebugTraceTest test_debug.cpp)

add_executable(M2PauseInterpolationTest test_pause.cpp)
