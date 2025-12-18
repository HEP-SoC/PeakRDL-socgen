from typing import TYPE_CHECKING
from jinja2.environment import nodes

from peakrdl.plugins.exporter import ExporterSubcommandPlugin #pylint: disable=import-error
from peakrdl.config import schema #pylint: disable=import-error

from systemrdl.node import AddrmapNode

from .__about__ import __version__
from .exporter import  SocExporter

if TYPE_CHECKING:
    import argparse



class Exporter(ExporterSubcommandPlugin):
    short_desc = "Generate SoC interconnections from a SystemRDL description."
    long_desc = "Generate SoC interconnections from a SystemRDL description."

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

        if options.list_files:
            soc.list_files(top_node, options.intfs, options.output)
        else:
            soc.export(
                top_node=top_node,
                outdir=options.output,
                intfs=options.intfs,
                vinject=options.vinject,
                use_include=options.use_include,
                gen_dot=options.gen_dot,
            )
