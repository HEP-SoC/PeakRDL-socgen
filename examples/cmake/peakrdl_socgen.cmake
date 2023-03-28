set(SOCGEN_DIR "${CMAKE_CURRENT_LIST_DIR}/../../src/peakrdl_socgen/")

function(peakrdl_socgen LIB)
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
    target_sources(${LIB} INTERFACE
        "${SOCGEN_DIR}/interconnects/nmi/nmi2apb.v"
        "${SOCGEN_DIR}/interconnects/nmi/nmi_tmr2nmi.v"
        "${SOCGEN_DIR}/interconnects/nmi/nmi2nmi_tmr.v"
        "${SOCGEN_DIR}/interconnects/apb/apb2apb_tmr.v"
        "${SOCGEN_DIR}/interconnects/apb/apb_tmr2apb.v"        
        "${SOCGEN_DIR}/interconnects/common/majorityVoter.v"        
        "${SOCGEN_DIR}/interconnects/common/fanout.v"        
        )

    foreach(bus ${ARG_BUSES})
        list(APPEND RDL_SOCGEN 
            "${SOCGEN_DIR}/interconnects/${bus}/${bus}_bus.rdl"
            )
        list(APPEND RDL_BUSES
            "${SOCGEN_DIR}/interconnects/${bus}/${bus}_bus.rdl"
            )
        target_sources(${LIB} INTERFACE
            "${SOCGEN_DIR}/interconnects/${bus}/${bus}_interconnect.v"
            )
    endforeach()

    if(NOT RDL_FILES STREQUAL "RDL_FILES-NOTFOUND")

        # Call peakrdl-socgen with --list-files option to get the list of headers
        execute_process(
            OUTPUT_VARIABLE V_GEN
            ERROR_VARIABLE SOCGEN_ERROR
            COMMAND peakrdl socgen
                --list-files
                ${RDL_SOCGEN} ${RDL_FILES}
                -o ${OUTDIR}
            )
        if(V_GEN)
            string(REPLACE " " ";" V_GEN "${V_GEN}")
            string(REPLACE "\n" "" V_GEN "${V_GEN}")
            list(REMOVE_DUPLICATES V_GEN)
        endif()

        set_source_files_properties(${V_GEN} PROPERTIES GENERATED TRUE)
        target_sources(${LIB} INTERFACE
            ${V_GEN}
            )

        message("SOCGEN: ${RDL_SOCGEN}")
        message("VGEN: ${V_GEN}")
        set(STAMP_FILE "${OUTDIR}/${LIB}_socgen.stamp")
        add_custom_command(
            OUTPUT ${V_GEN} ${STAMP_FILE}
            COMMAND peakrdl socgen 
                --buses ${RDL_BUSES}
                -o ${OUTDIR} 
                ${RDL_SOCGEN} ${RDL_FILES}

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

if(NOT TARGET graphviz)
    add_custom_target(graphviz
        COMMAND ${CMAKE_COMMAND} -E copy ${CMAKE_CURRENT_LIST_DIR}/CMakeGraphVizOptions.cmake ${CMAKE_BINARY_DIR}
        COMMAND ${CMAKE_COMMAND} "--graphviz=graphviz/foo.dot" .
        COMMAND python3 ${CMAKE_CURRENT_LIST_DIR}/graphviz_shorten_path.py -f "${CMAKE_BINARY_DIR}/graphviz/foo.dot" -o "${CMAKE_BINARY_DIR}/graphviz/out.dot" -l
        COMMAND dot -Tpng "${CMAKE_BINARY_DIR}/graphviz/out.dot" -o graph.png
        WORKING_DIRECTORY "${CMAKE_BINARY_DIR}"
    )
endif()
