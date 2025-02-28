# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2025 CERN
#
# Please retain this header in all redistributions and modifications of the code.

cmake_minimum_required(VERSION 3.25)
project(axi_soc NONE)

include("deps/deps.cmake")

add_library(${PROJECT_NAME} INTERFACE
    )

set_property(TARGET ${PROJECT_NAME} PROPERTY RDL_FILES
    ${PROJECT_SOURCE_DIR}/axi_slave.rdl
    ${PROJECT_SOURCE_DIR}/apb_slave.rdl
    ${PROJECT_SOURCE_DIR}/apb_subsys.rdl
    ${PROJECT_SOURCE_DIR}/axi_master.rdl
    ${PROJECT_SOURCE_DIR}/axi_soc.rdl
    )

target_link_libraries(${PROJECT_NAME} INTERFACE
    socgen
    socgen_apb
    socgen_axi
    )

peakrdl_socgen(${PROJECT_NAME})
