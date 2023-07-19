from typing import TYPE_CHECKING
from jinja2.environment import nodes

from peakrdl.plugins.exporter import ExporterSubcommandPlugin #pylint: disable=import-error
from peakrdl.config import schema #pylint: disable=import-error

from .exporter import  SocExporter

if TYPE_CHECKING:
    import argparse
    from systemrdl.node import AddrmapNode


class Exporter(ExporterSubcommandPlugin):
    short_desc = "Generate CPP Hardware Abstraction Layer libraries"
    long_desc = "Generate CPP Hardware Abstraction Layer libraries"


    def add_exporter_arguments(self, arg_group: 'argparse.ArgumentParser') -> None:

        arg_group.add_argument(
                "--intfs",
                nargs="*", 
                help="list of intfs"
                )

        arg_group.add_argument(
                "--vinject",
                nargs="*", 
                default=[],
                help="List of files to inject into the generated subsystems. If you want to inject a file into a subsystem called apb_subsystem, you need to name your file apb_subsystem_inj_<some_name>.v/sv"
                )

        arg_group.add_argument(
            "--use-include",
            dest="use_include",
            default=False,
            action="store_true",
            help="Use verilog include directive to include files specified with --vinject flag. By default content of files are injected into the generated sources"
        )

        arg_group.add_argument(
            "--list-files",
            dest="list_files",
            default=False,
            action="store_true",
            help="Dont generate files, but instead just list the files that will be generated, and external files that need to be included"
        )


    def do_export(self, top_node: 'AddrmapNode', options: 'argparse.Namespace') -> None:
        soc = SocExporter(
        )
        
        if options.list_files:
            soc.list_files(top_node, options.output)
        else:
            soc.export(
                nodes=top_node,
                outdir=options.output,
                intfs=options.intfs,
                vinject=options.vinject,
                use_include=options.use_include,
            )
