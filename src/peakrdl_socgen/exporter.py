# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2025 CERN
#
# Please retain this header in all redistributions and modifications of the code.

import os
import jinja2
import logging
from typing import  Dict, Any, List
from datetime import datetime
from systemrdl.node import Node, RootNode
from systemrdl import AddrmapNode, RDLCompiler, RDLWalker

from .__about__ import __version__
from .subsystem import Subsystem, SubsystemListener

# Logger generation for halnode module
export_logger = logging.getLogger("export_logger")
# Console handler
ch = logging.StreamHandler()
# create formatter and add it to the handlers
formatter = logging.Formatter('%(name)s - %(levelname)s: %(message)s')
ch.setFormatter(formatter)
# add the handlers to the logger
export_logger.addHandler(ch)

# Set for more verbosity
export_logger.setLevel(logging.INFO)

class SocExporter():
    def __init__(self):
        # Template used to generate a subsystem verilog file from a SystemRDL description
        self.subsystem_template = "subsystem.sv.j2"
        self.subsystem_ext = "." + self.subsystem_template.split(".")[1]
        self.addrmap_pkg_template = "soc_addr_map_pkg.sv.j2"
        self.dot_template = "soc_diagram.dot.j2"

    @staticmethod
    def dot_to_uscore(in_str: str):
        """Replaces '.' with '_' in a string."""
        return in_str.replace(".", "_")

    @staticmethod
    def get_file_content(file: str) -> str:
        """Returns a file content as a string."""
        ret_str = ""
        with open(file, "r") as f:
            ret_str = f.read()
        return ret_str

    @staticmethod
    def get_file_name(file: str) -> str:
        """Returns the base name of a file path."""
        return os.path.basename(file)

    @staticmethod
    def short_str(string: str, length: int = 20) -> str:
        """Abbreviates a string with '...' if its longer than a given length."""
        if len(string) > length:
            return string[0:length] + "..."
        return string

    # def getNodeName(self, node: Node) -> str:
    #     """Returns the orig_type_name or the inst_name in case the former does not exist."""
    #     if node.orig_type_name is not None:
    #         return node.orig_type_name
    #     else:
    #         return node.inst_name

    def list_files(self, top_node: 'AddrmapNode', intfs: 'List[str]', outdir: str):
        """List the files that will generated."""

        # Retrieve the AddrmapNodes with the 'subsystem' property set
        walker = RDLWalker(unroll=True)
        listener = SubsystemListener()
        walker.walk(top_node, listener)
        rdlc = self.compile_glue(intfs)
        subsystems = [Subsystem(x, rdlc) for x in listener.subsystem_nodes]

        out_files = [os.path.join(outdir, self.addrmap_pkg_template.replace(".j2", ""))]
        out_files += [os.path.join(outdir, s.getOrigTypeName() + self.subsystem_ext) for s in subsystems]

        # Print files to stdout
        print(*out_files)

    def compile_glue(self, list_intf_files: List[str]):
        """Compile and append intf files to a new RDLCompiler instance."""
        rdlc = RDLCompiler()
        for input_file in list_intf_files:
            rdlc.compile_file(input_file)
        # Elaborate to check there is at list one valid addrmap
        # The last addrmap seen is used as the top-level by default
        rdlc.elaborate()
        return rdlc

    def export(self,
               top_node: 'AddrmapNode',
               outdir: str,
               intfs: 'List[str]',
               vinject: 'List[str]',
               use_include: bool = False,
               gen_dot: bool = False,
               **kwargs: 'Dict[str, Any]'
               ):

        # Check for any unused additional arguments
        if kwargs:
            raise TypeError("Got an unexpected keyword argument '%s'" % list(kwargs.keys())[0])

        # Generate the output directory where generated files will be saved
        try:
            os.makedirs(outdir)
        except FileExistsError:
            export_logger.info(f'Output directory {outdir} already exists.')
            pass

        # This plugin uses to different compiler instances:
        # 1. The default one called by this plugin and producing the top_node
        # 2. A second one (below) that execute on the intfs files listed. This
        #    files are not compiled by the first compiler, but passed as arguments
        #    using the --intfs parameter.
        rdlc = self.compile_glue(intfs)

        # Retrieve the AddrmapNodes with the 'subsystem' property set
        walker = RDLWalker(unroll=True)
        listener = SubsystemListener()
        walker.walk(top_node, listener)
        subsystems = [Subsystem(x, rdlc) for x in listener.subsystem_nodes]

        date_time_now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

        for subsys in subsystems:
            export_logger.info(f'Generating subsystem {subsys.node.inst_name}.')
            subsys_inj_files = []
            for inj_f in vinject:
                # Get the inject files matching the node name
                if os.path.basename(inj_f).startswith(subsys.getOrigTypeName()):
                    subsys_inj_files.append(inj_f)

            # Context for the jinja template
            context = {
                'subsys': subsys,
                'inj_f': subsys_inj_files,
                'use_include': use_include,
                'socgen_version': __version__,
                'date_time': date_time_now,
            }
            # Generate the subsystem files
            text = self.process_subsystem_template(context, self.subsystem_template)
            # Generate the file absolute path
            out_file = os.path.join(outdir, subsys.getOrigTypeName() + self.subsystem_ext)
            # Write the content to the file
            with open(out_file, 'w') as f:
                f.write(text)

        # Generate the addrmap package file
        text = self.process_arrdmap_pkg_template(subsystems, date_time_now, self.addrmap_pkg_template)
        # Generate the file absolute path
        out_file = os.path.join(outdir, self.addrmap_pkg_template.replace(".j2", ""))
        # Write the content to the file
        with open(out_file, 'w') as f:
            f.write(text)


        # Generate the graph dot file if flag is set
        if gen_dot:
            context = {
                'subsystems': subsystems,
                'socgen_version': __version__,
                'date_time': date_time_now,
            }
            # Generate the file content
            text = self.process_dot_template(context, self.dot_template)
            # Generate the file absolute path
            out_file = os.path.join(outdir, self.dot_template.replace(".j2", ""))
            # Write the content to the file
            with open(out_file, 'w') as f:
                f.write(text)

    def process_arrdmap_pkg_template(self, subsystems, date_time_now, template: str) -> str:
        """Template processing for addrmap package generation."""

        # for subsys in subsystems:
        #     for intc in subsys.intcs:
        #         print(f"\t intc: {intc.inst_name} @0x{intc.subsystem_node.inst.addr_offset:08x}")

        #         for mstp in intc.ext_mst_ports:
        #             print(f"\t\t mst port: {mstp.module.node.inst_name}.{mstp.node.inst_name}")
        #             print(f"\t\t\t byte size   : {mstp.module.node.size}")
        #             print(f"\t\t\t addr_offset: 0x{mstp.module.node.inst.addr_offset:08x}")
        #         for slvp in intc.ext_slv_ports:
        #             print(f"\t\t slv port: {slvp.module.node.inst_name}.{slvp.node.inst_name}")
        #             print(f"\t\t\t byte size   : {slvp.module.node.size}")
        #             print(f"\t\t\t addr_offset: 0x{slvp.module.node.inst.addr_offset:08x}")
        #         for param in intc.hdl_params:
        #             print(f"{param['name']}: {param['value']}")

        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader('%s/templates/' % os.path.dirname(__file__)),
            # trim_blocks=True,
            lstrip_blocks=True
        )

        context = {
            'subsystems': subsystems,
            'RootNode'  : RootNode,
            'socgen_version': __version__,
            'date_time': date_time_now,
        }

        res = env.get_template(template).render(context)
        return res

    def process_subsystem_template(self, context: dict, template: str) -> str:
        """Template processing for subsystem generation."""
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader('%s/templates/' % os.path.dirname(__file__)),
            trim_blocks=True,
            lstrip_blocks=True)

        env.filters.update({
            'int': int,
            'path_conv': SocExporter.dot_to_uscore,
            'get_file_content': SocExporter.get_file_content,
            'get_file_name': SocExporter.get_file_name,
        })

        res = env.get_template(template).render(context)
        return res

    def process_dot_template(self, context: dict, template: str) -> str:
        """Template processing for the grap dot file generation."""
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader('%s/templates/' % os.path.dirname(__file__)),
            trim_blocks=True,
            extensions=['jinja2.ext.loopcontrols'],
            lstrip_blocks=True)

        env.filters.update({
            'path_conv': SocExporter.dot_to_uscore,
            'short': SocExporter.short_str,
        })

        res = env.get_template(template).render(context, zip=zip)
        return res
