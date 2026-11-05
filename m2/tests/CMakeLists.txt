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

add_executable(M2ReleaseSelectorTest test_update_release_selector.cpp)
add_executable(M2SmokeAnimationTest test_smoke_animation.cpp)

add_executable(M2CoinSpriteTraceTest test_coin_sprite.cpp)
add_executable(M2ImageIdentityTest test_image_identity.cpp)
add_executable(M2CoinAnimationTest test_coin_animation.cpp)
add_executable(M2PixelEquivalenceTest test_pixel_equivalence.cpp)
add_executable(M2CoinBenchmark benchmark_coin_animation.cpp)
target_include_directories(M2CoinBenchmark PRIVATE ..)
set_property(TARGET M2CoinBenchmark PROPERTY MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/baseline_headers/CoinAnimation.hpp")
    add_executable(M2CoinBenchmarkBaseline benchmark_coin_animation.cpp)
    target_include_directories(M2CoinBenchmarkBaseline PRIVATE baseline_headers)
    set_property(TARGET M2CoinBenchmarkBaseline PROPERTY MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")
endif()
