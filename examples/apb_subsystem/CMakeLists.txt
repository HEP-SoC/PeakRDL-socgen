
cmake_minimum_required(VERSION 3.25)
project(apb_subsystem VERSION 1.0)

include("../cmake/peakrdl_socgen.cmake")
include("../cmake/iverilog.cmake")
include("../cmake/verilate.cmake")

# set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
# set(CMAKE_VERBOSE_MAKEFILE ON)

add_library(rtllib INTERFACE EXCLUDE_FROM_ALL
    "${PROJECT_SOURCE_DIR}/verilog/tb.v"
    "${PROJECT_SOURCE_DIR}/verilog/apb_master.v"
    "${PROJECT_SOURCE_DIR}/verilog/simple_apb_slave.v"
    )

set_property(TARGET rtllib PROPERTY RDL_FILES 
    "${PROJECT_SOURCE_DIR}/rdl/apb_master.rdl"
    "${PROJECT_SOURCE_DIR}/rdl/simple_apb_slave.rdl"
    "${PROJECT_SOURCE_DIR}/rdl/apb_subsystem.rdl"
    )

peakrdl_socgen(rtllib BUSES apb)
iverilog(rtllib)

verilator(${PROJECT_NAME} rtllib EXCLUDE_FROM_ALL
    TOP_MODULE tb
    )
