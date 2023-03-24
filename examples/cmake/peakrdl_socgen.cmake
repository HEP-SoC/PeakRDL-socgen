set(SOCGEN_DIR "${CMAKE_CURRENT_LIST_DIR}/../../src/peakrdl_socgen/")

function(peakrdl_socgen LIB BUS)
    cmake_parse_arguments(ARG "" "OUTDIR" "" ${ARGN})

    get_target_property(BINARY_DIR ${LIB} BINARY_DIR)

    if(NOT ARG_OUTDIR)
        set(OUTDIR ${BINARY_DIR}/socgen)
    else()
        set(OUTDIR ${ARG_OUTDIR})
    endif()

    get_target_property(RDL_FILES ${LIB} RDL_FILES)

    set(RDL_SOCGEN
        "${SOCGEN_DIR}/common.rdl"
        )
    if(BUS STREQUAL "nmi")
        list(APPEND RDL_SOCGEN 
            "${SOCGEN_DIR}/interconnects/nmi/nmi_bus.rdl"
            )
    elseif(BUS STREQUAL "apb")
        list(APPEND RDL_SOCGEN 
            "${SOCGEN_DIR}/interconnects/apb/apb_bus.rdl"
            )
    endif()

    if(NOT RDL_FILES STREQUAL "RDL_FILES-NOTFOUND")

        set(V_GEN "${OUTDIR}/${BUS}_subsystem.v")

        set_source_files_properties(${V_GEN} PROPERTIES GENERATED TRUE)
        target_sources(${LIB} INTERFACE
            ${V_GEN}
            )

        set(STAMP_FILE "${OUTDIR}/${LIB}_socgen.stamp")
        add_custom_command(
            OUTPUT ${V_GEN} ${STAMP_FILE}
            COMMAND peakrdl socgen 
                ${RDL_SOCGEN} ${RDL_FILES}
                -o ${OUTDIR} 

            COMMAND touch ${STAMP_FILE}
            DEPENDS ${RDL_FILES}
            COMMENT "Running peakrdl socgen on ${LIB}"
            )

        add_custom_target(
            ${LIB}_socgen
            DEPENDS ${V_GEN} ${STAMP_FILE}
            )

        add_dependencies(${LIB} ${LIB}_socgen)

    endif()

endfunction()
