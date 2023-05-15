cmake_minimum_required(VERSION 3.25)
project(pulpif NONE)

add_library(pulpif INTERFACE
    ${PROJECT_SOURCE_DIR}/pulpif_interconnect.sv
    )

add_subdirectory(pulpif2axi)
target_link_libraries(pulpif INTERFACE pulpif2axi)

set_property(TARGET pulpif PROPERTY RDL_INTF_INTERCONNECTS
    ${PROJECT_SOURCE_DIR}/pulpif_interconnect.rdl
    )
set_property(TARGET pulpif PROPERTY RDL_INTF
    ${PROJECT_SOURCE_DIR}/pulpif_intf.rdl
    )

set_property(TARGET pulpif PROPERTY RDL_INTF_ADAPTERS
    ${PROJECT_SOURCE_DIR}/pulpif_adapt_to.rdl
    )


