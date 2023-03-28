set(SOCGEN_DIR "${CMAKE_CURRENT_LIST_DIR}/../../../src/peakrdl_socgen/")
set(GEN_MMAP_DIR ${CMAKE_CURRENT_LIST_DIR})

function(gen_mmap TARGET LIB)
    cmake_parse_arguments(ARG "" "OUTDIR" "BUSES" ${ARGN})

    get_target_property(BINARY_DIR ${LIB} BINARY_DIR)

    if(NOT ARG_OUTDIR)
        set(OUTDIR ${BINARY_DIR}/socgen)
    else()
        set(OUTDIR ${ARG_OUTDIR})
    endif()

    get_target_property(RDL_FILES ${LIB} RDL_FILES)

    set(RDL_SOCGEN
        "${SOCGEN_DIR}/rdl/common.rdl"
        )
    foreach(bus ${ARG_BUSES})
        list(APPEND RDL_SOCGEN 
            "${SOCGEN_DIR}/interconnects/${bus}/${bus}_bus.rdl"
            )
    endforeach()
    message("RDL_SOSCGEN: ${RDL_SOCGEN}")

    if(NOT RDL_FILES STREQUAL "RDL_FILES-NOTFOUND")

        # Call peakrdl-socgen with --list-files option to get the list of headers
        set(MMAP_FILE "${OUTDIR}/mmap.cpp")
        message("MMAP_FILE: ${MMAP_FILE}")
        set_source_files_properties(${MMAP_FILE} PROPERTIES GENERATED TRUE)
        target_sources(${TARGET} PUBLIC
            ${MMAP_FILE}
            )

        set(STAMP_FILE "${OUTDIR}/${LIB}_mmap.stamp")
        add_custom_command(
            OUTPUT ${MMAP_FILE} ${STAMP_FILE}
            COMMAND  python3 "${GEN_MMAP_DIR}/gen_mmap.py"
                ${OUTDIR}
                ${RDL_SOCGEN} ${RDL_FILES}

            COMMAND touch ${STAMP_FILE}
            DEPENDS ${RDL_FILES}
            COMMENT "Generating mmap file for ${LIB}"
            )

        add_custom_target(
            ${LIB}_mmap
            DEPENDS ${MMAP_FILE} ${STAMP_FILE}
            )

        add_dependencies(${TARGET} ${LIB}_mmap)
    endif()
endfunction()
