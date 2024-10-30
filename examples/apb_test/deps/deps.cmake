option(UPDATE_PYTHON_DEPS "Force update dependencies" OFF)
option(DEPS_USE_VENV "Create a Python virtual environment and install dependencies locally" ON)
option(UPDATE_DEPS "Update all of the dependencies, CPM packages and Python" OFF)

include("${CMAKE_CURRENT_LIST_DIR}/venv.cmake")

set(FETCHCONTENT_BASE_DIR ${CMAKE_CURRENT_LIST_DIR}/_deps CACHE INTERNAL "")
set(CPM_DOWNLOAD_VERSION 0.38.1)             # Define CPM version to be downloaded
include(${CMAKE_CURRENT_LIST_DIR}/CPM.cmake) # Include the CPM.cmake downloader

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
