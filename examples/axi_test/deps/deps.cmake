set(CPM_DOWNLOAD_VERSION 0.38.1)
include(${CMAKE_CURRENT_LIST_DIR}/CPM.cmake)

CPMAddPackage(
    NAME SoCMake
    GIT_TAG v0.2.16
    GIT_REPOSITORY "git@github.com:HEP-SoC/SoCMake.git"
)

CPMAddPackage(
    NAME socgen_interconnects
    GIT_TAG v0.1.9
    GIT_REPOSITORY "ssh://git@gitlab.cern.ch:7999/socrates/ip_blocks/socgen_interconnects.git"
)
