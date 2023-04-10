cmake_minimum_required(VERSION 3.25)
project(picorvino VERSION 1.0)

include("../cmake/peakrdl_socgen.cmake")
include("../cmake/verilate.cmake")


set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(CMAKE_VERBOSE_MAKEFILE ON)

add_library(rtllib INTERFACE EXCLUDE_FROM_ALL
    "${PROJECT_SOURCE_DIR}/verilog/nmi_memory.v"
    "${PROJECT_SOURCE_DIR}/picorv32/picorv32.v"
    "${PROJECT_SOURCE_DIR}/vrf/picorvino_wrap.v"
    )

set_property(TARGET rtllib PROPERTY RDL_FILES 
    "${PROJECT_SOURCE_DIR}/rdl/nmi_memory.rdl"
    "${PROJECT_SOURCE_DIR}/picorv32/picorv32.rdl"
    "${PROJECT_SOURCE_DIR}/picorvino.rdl"
    )

peakrdl_socgen(rtllib BUSES nmi)

add_executable(${PROJECT_NAME}
    ${PROJECT_SOURCE_DIR}/vrf/main.cpp
    )
# target_include_directories(${PROJECT_NAME} PUBLIC
#     ${PROJECT_SOURCE_DIR}
#     )

verilator(${PROJECT_NAME} rtllib EXCLUDE_FROM_ALL
    TOP_MODULE picorvino_wrap 
    VERILATOR_ARGS --Wno-fatal
    TRACE
    )

# add_dependencies(rtllib_iverilog apb_subsystem_socgen)


