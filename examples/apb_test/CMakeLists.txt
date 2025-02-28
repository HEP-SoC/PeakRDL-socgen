# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2025 CERN
#
# Please retain this header in all redistributions and modifications of the code.

cmake_minimum_required(VERSION 3.25)
project(apb_soc NONE)

include("deps/deps.cmake")

add_ip(${PROJECT_NAME}
    VENDOR cern
    LIBRARY ip
    VERSION 0.0.1
)


ip_sources(${IP} SYSTEMRDL
    ${PROJECT_SOURCE_DIR}/apb_slave.rdl
    ${PROJECT_SOURCE_DIR}/apb_master.rdl
    ${PROJECT_SOURCE_DIR}/apb_soc.rdl
)

ip_link(${IP}
    cern::socgen::base
    cern::socgen::apb
    )

peakrdl_socgen(${PROJECT_NAME})
