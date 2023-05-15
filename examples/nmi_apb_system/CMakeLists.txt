cmake_minimum_required(VERSION 3.25)
project(nmi_system VERSION 1.0)

include("../cmake/peakrdl_socgen.cmake")
include("../cmake/iverilog.cmake")
include("../cmake/verilate.cmake")
include("scripts/gen_mmap.cmake")


set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(CMAKE_VERBOSE_MAKEFILE ON)

add_library(rtllib INTERFACE EXCLUDE_FROM_ALL
    "${PROJECT_SOURCE_DIR}/verilog/apb_memory.v"
    "${PROJECT_SOURCE_DIR}/verilog/nmi_memory.v"
    )

set_property(TARGET rtllib PROPERTY RDL_FILES 
    "${PROJECT_SOURCE_DIR}/rdl/apb_memory.rdl"
    "${PROJECT_SOURCE_DIR}/rdl/nmi_memory.rdl"
    "${PROJECT_SOURCE_DIR}/rdl/apb_subsystem.rdl"
    "${PROJECT_SOURCE_DIR}/rdl/nmi_system.rdl"
    )

peakrdl_socgen(rtllib BUSES nmi apb)
# iverilog(rtllib)

add_executable(${PROJECT_NAME}
    ${PROJECT_SOURCE_DIR}/main.cpp
    )
target_include_directories(${PROJECT_NAME} PUBLIC
    ${PROJECT_SOURCE_DIR}
    )

gen_mmap(${PROJECT_NAME} rtllib BUSES apb nmi)
verilator(${PROJECT_NAME} rtllib EXCLUDE_FROM_ALL
    TOP_MODULE nmi_system
    )

# add_dependencies(rtllib_iverilog apb_subsystem_socgen)

