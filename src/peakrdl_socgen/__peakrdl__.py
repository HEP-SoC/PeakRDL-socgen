from typing import TYPE_CHECKING
from jinja2.environment import nodes

from peakrdl.plugins.exporter import ExporterSubcommandPlugin #pylint: disable=import-error
from peakrdl.config import schema #pylint: disable=import-error
from peakrdl.process_input import process_input #pylint: disable=import-error

from systemrdl import RDLCompiler
from systemrdl.node import AddrmapNode

from .__about__ import __version__
from .exporter import  SocExporter
from .tmr import TMR_UDPS, TmrConfig, register_tmr_udps

if TYPE_CHECKING:
    import argparse



class Exporter(ExporterSubcommandPlugin):
    short_desc = "Generate SoC interconnections from a SystemRDL description."
    long_desc = "Generate SoC interconnections from a SystemRDL description."

    udp_definitions = TMR_UDPS

    def add_exporter_arguments(self, arg_group: 'argparse.ArgumentParser') -> None:

        arg_group.add_argument(
                "--intfs",
                nargs="*",
                help="List of SystemRDL extension files describing possible interfaces/interconnection."
                )

        arg_group.add_argument(
                "--vinject",
                nargs="*",
                default=[],
                help="List of files to inject into the generated subsystems. \
                    If you want to inject a file into a subsystem called apb_subsystem, \
                    you need to name your file apb_subsystem_inj_<some_name>.v/sv"
                )

        arg_group.add_argument(
            "--use-include",
            dest="use_include",
            default=False,
            action="store_true",
            help="Use verilog include directive to include files specified with --vinject flag. \
                By default content of files are injected into the generated sources"
        )

        arg_group.add_argument(
            "--list-files",
            dest="list_files",
            default=False,
            action="store_true",
            help="Dont generate files, but instead just list the files that will be generated, \
                and external files that need to be included"
        )

        arg_group.add_argument(
            "--gen-dot",
            dest="gen_dot",
            default=False,
            action="store_true",
            help="Generate also block diagram of the generated SoC in graphviz dot format."
        )

        arg_group.add_argument(
            "--tmr",
            dest="tmr",
            default=False,
            action="store_true",
            help="Generate the TMR version of the SoC from its non-TMR description: subsystem signals are \
                triplicated, interfaces are mapped to their TMR counterpart (see the tmr_intf property), \
                and leaf modules are replaced by their TMR definition (<type_name><suffix> or tmr_type)."
        )

        arg_group.add_argument(
            "--tmr-suffix",
            dest="tmr_suffix",
            default="TMR",
            help="Suffix appended to the non-TMR type names in TMR mode (default: TMR)."
        )

        arg_group.add_argument(
            "--intf-map",
            dest="intf_map",
            nargs="*",
            default=[],
            metavar="INTF=TMR_INTF",
            help="Non-TMR to TMR interface struct mapping overriding the tmr_intf property \
                of the interface nodes (e.g., apb_intf=apb_rt_intf)."
        )

        arg_group.add_argument(
            "--intc-pkg",
            dest="intc_pkg",
            default=False,
            action="store_true",
            help="Generate the interconnect configuration (number of ports, indexes, and address rules) in a \
                separate <top>_intc_pkg package. soc_addr_map_pkg then only contains the memory map, including \
                the slaves not present in the design (ispresent = false), so it is the same for all the designs \
                generated from a SystemRDL description (e.g., non-TMR and TMR)."
        )

        arg_group.add_argument(
            "-v", "--version",
            dest="version",
            action="version",
            version='%(prog)s ' + __version__
        )

    def do_export(self, top_node: 'AddrmapNode', options: 'argparse.Namespace') -> None:
        """Plugin entry function."""
        # SoCgen exporter plugin
        soc = SocExporter()

        # Check the top_node is an AddrmapNode object
        if not isinstance(top_node, AddrmapNode):
            raise TypeError(
                "'top_node' argument expects type AddrmapNode. Got '%s'" % type(top_node).__name__)

        tmr = self.get_tmr_config(options) if options.tmr else None

        if options.list_files:
            soc.list_files(top_node, options.intfs, options.output, tmr=tmr, intc_pkg=options.intc_pkg)
        else:
            soc.export(
                top_node=top_node,
                outdir=options.output,
                intfs=options.intfs,
                vinject=options.vinject,
                use_include=options.use_include,
                gen_dot=options.gen_dot,
                tmr=tmr,
                intc_pkg=options.intc_pkg,
            )

    @staticmethod
    def get_tmr_config(options: 'argparse.Namespace') -> TmrConfig:
        """Returns the TMR mode options.

        The TMR definitions of the leaf modules are not part of the elaborated non-TMR design, so the
        input files are compiled again in a compiler from which they can be elaborated by name.
        """
        design_rdlc = RDLCompiler()
        register_tmr_udps(design_rdlc)
        process_input(design_rdlc, [], options.input_files, options)

        intf_map = {}
        for mapping in options.intf_map:
            base_intf, sep, tmr_intf = mapping.partition("=")
            if not sep or not base_intf or not tmr_intf:
                raise ValueError(f"Invalid --intf-map argument: {mapping}. Use INTF=TMR_INTF.")
            intf_map[base_intf] = tmr_intf

        return TmrConfig(design_rdlc=design_rdlc, suffix=options.tmr_suffix, intf_map=intf_map)
