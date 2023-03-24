include("../cmake/peakrdl_socgen.cmake")
include("../cmake/iverilog.cmake")

cmake_minimum_required(VERSION 3.25)
project(nmi_test VERSION 1.0)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(CMAKE_VERBOSE_MAKEFILE ON)

add_library(${PROJECT_NAME} INTERFACE
    "${PROJECT_SOURCE_DIR}/verilog/tb.v"
    "${PROJECT_SOURCE_DIR}/verilog/nmi_master.v"
    "${PROJECT_SOURCE_DIR}/verilog/nmi_memory.v"
    )

set_property(TARGET ${PROJECT_NAME} PROPERTY RDL_FILES 
    "${PROJECT_SOURCE_DIR}/rdl/signals.rdl"
    "${PROJECT_SOURCE_DIR}/rdl/nmi_master.rdl"
    "${PROJECT_SOURCE_DIR}/rdl/nmi_memory.rdl"
    "${PROJECT_SOURCE_DIR}/rdl/nmi_subsystem.rdl"
    )

peakrdl_socgen(${PROJECT_NAME} "nmi")
iverilog(${PROJECT_NAME})
