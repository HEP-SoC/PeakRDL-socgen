include_guard(GLOBAL)
cmake_minimum_required(VERSION 3.25)
project(pulp_axi NONE)

add_library(pulp_axi INTERFACE
    ${PROJECT_SOURCE_DIR}/axi_intf.sv
    ${PROJECT_SOURCE_DIR}/axi_pkg.sv
    ${PROJECT_SOURCE_DIR}/typedef.svh
    ${PROJECT_SOURCE_DIR}/registers.svh
    )


target_include_directories(pulp_axi INTERFACE
    ${PROJECT_SOURCE_DIR}
    )

