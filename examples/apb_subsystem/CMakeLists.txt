include("../cmake/peakrdl_socgen.cmake")
include("../cmake/iverilog.cmake")

cmake_minimum_required(VERSION 3.25)
project(apb_test VERSION 1.0)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(CMAKE_VERBOSE_MAKEFILE ON)

add_library(${PROJECT_NAME} INTERFACE
    "${PROJECT_SOURCE_DIR}/verilog/tb.v"
    "${PROJECT_SOURCE_DIR}/verilog/apb_master.v"
    "${PROJECT_SOURCE_DIR}/verilog/simple_apb_slave.v"
    )

set_property(TARGET ${PROJECT_NAME} PROPERTY RDL_FILES 
    "${PROJECT_SOURCE_DIR}/rdl/signals.rdl"
    "${PROJECT_SOURCE_DIR}/rdl/apb_master.rdl"
    "${PROJECT_SOURCE_DIR}/rdl/simple_apb_slave.rdl"
    "${PROJECT_SOURCE_DIR}/rdl/apb_subsystem.rdl"
    )

peakrdl_socgen(${PROJECT_NAME} "apb")
iverilog(${PROJECT_NAME})

