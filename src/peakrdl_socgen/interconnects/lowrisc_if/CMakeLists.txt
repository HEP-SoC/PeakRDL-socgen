cmake_minimum_required(VERSION 3.25)
project(lowrisc_if NONE)

add_library(lowrisc_if INTERFACE)

add_subdirectory("rtl/pulp_adapters/")

target_link_libraries(lowrisc_if INTERFACE axi2lowrisc_if)
add_dependencies(lowrisc_if axi2lowrisc_if)

# set_property(TARGET lowrisc_if PROPERTY RDL_DEPS
#     ${PROJECT_SOURCE_DIR}/axi2lowrisc_if.rdl
#     ${PROJECT_SOURCE_DIR}/lowrisc_if_intf.rdl
#     )

