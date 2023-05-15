cmake_minimum_required(VERSION 3.25)
project(pulpif2axi NONE)

add_library(pulpif2axi INTERFACE
    ${PROJECT_SOURCE_DIR}/pulpif2axi.sv
    ${PROJECT_SOURCE_DIR}/pulpif2axi_lite.sv

    ${PROJECT_SOURCE_DIR}/axi_from_mem.sv
    ${PROJECT_SOURCE_DIR}/axi_lite_from_mem.sv
    ${PROJECT_SOURCE_DIR}/axi_lite_to_axi.sv
    ${PROJECT_SOURCE_DIR}/fifo_v3.sv

    )

add_subdirectory("../pulp_axi" "pulp_axi")
target_link_libraries(pulpif2axi INTERFACE pulp_axi)


# include("../../../cmake/verilate.cmake")
#
# verilator(tb pulpif2axi
#     TOP_MODULE pulpif2axi
#     VERILATOR_ARGS -Wno-fatal
#     TRACE
#     )
