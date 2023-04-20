cmake_minimum_required(VERSION 3.25)
project(axi2lowrisc_if NONE)

add_library(${PROJECT_NAME} INTERFACE
    ${PROJECT_SOURCE_DIR}/axi2lowrisc_if.sv
    ${PROJECT_SOURCE_DIR}/axi_w_buffer.sv
    ${PROJECT_SOURCE_DIR}/axi_b_buffer.sv
    ${PROJECT_SOURCE_DIR}/axi_r_buffer.sv
    ${PROJECT_SOURCE_DIR}/axi_ar_buffer.sv
    ${PROJECT_SOURCE_DIR}/axi_aw_buffer.sv
    ${PROJECT_SOURCE_DIR}/axi_read_only_ctrl.sv
    ${PROJECT_SOURCE_DIR}/axi_write_only_ctrl.sv
    ${PROJECT_SOURCE_DIR}/axi_single_slice.sv
    ${PROJECT_SOURCE_DIR}/pulp_fifo.sv
    )

