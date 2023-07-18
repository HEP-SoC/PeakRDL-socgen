cmake_minimum_required(VERSION 3.25)
project(apb_soc NONE)

include("deps/deps.cmake")

add_library(${PROJECT_NAME} INTERFACE
    )

set_property(TARGET ${PROJECT_NAME} PROPERTY RDL_FILES 
    ${PROJECT_SOURCE_DIR}/apb_slave.rdl
    ${PROJECT_SOURCE_DIR}/apb_master.rdl
    ${PROJECT_SOURCE_DIR}/apb_soc.rdl
    )

target_link_libraries(${PROJECT_NAME} INTERFACE
    socgen
    socgen_apb
    )

peakrdl_socgen(${PROJECT_NAME})
