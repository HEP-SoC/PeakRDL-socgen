set(SOCGEN_DIR "${CMAKE_CURRENT_LIST_DIR}/../../src/peakrdl_socgen/")

function(iverilog LIB)
    cmake_parse_arguments(ARG "" "OUTDIR" "" ${ARGN})

    get_target_property(BINARY_DIR ${LIB} BINARY_DIR)

    if(NOT ARG_OUTDIR)
        set(OUTDIR ${BINARY_DIR})
    else()
        set(OUTDIR ${ARG_OUTDIR})
    endif()

    get_target_property(V_SOURCES ${LIB} SOURCES)
    get_target_property(V_IF_SOURCES ${LIB} INTERFACE_SOURCES)
    set(V_FILES ${V_SOURCES} ${V_IF_SOURCES})
    list(REMOVE_DUPLICATES V_FILES)


    set(EXEC "${OUTDIR}/a.out")

    set(STAMP_FILE "${OUTDIR}/${LIB}_iverilog.stamp")
    add_custom_command(
        OUTPUT ${EXEC} ${STAMP_FILE}
        COMMAND iverilog
        ${V_FILES}
        COMMAND touch ${STAMP_FILE}
        DEPENDS ${RDL_FILES} ${V_FILES}
        COMMENT "Running iverilog on ${LIB}"
        )

    add_custom_target(
        ${LIB}_iverilog
        DEPENDS ${EXEC} ${STAMP_FILE} ${V_FILES}
        )

    add_custom_target(
        run_${LIB}
        COMMAND exec ${EXEC}
        BYPRODUCTS "${OUTDIR}/test1.vcd"
        DEPENDS ${EXEC} ${STAMP_FILE} ${V_FILES}
        )

    add_dependencies(${LIB} ${LIB}_iverilog)

endfunction()
