from typing import Optional, Dict, Any, Type, TYPE_CHECKING
from systemrdl import Addrmap, RDLCompiler, RDLCompileError
from systemrdl import RDLWalker, RDLListener
from systemrdl.core.parameter import Parameter
from systemrdl.node import  Node, RootNode, AddrmapNode, AddressableNode
from systemrdl.rdltypes.user_struct import UserStruct, UserStructMeta
from typing import List, Union
from copy import deepcopy
import os
import sys
import shutil
import jinja2

from .subsystem import Subsystem, SubsystemListener, getOrigTypeName
from .bus import create_bus

class SocExporter():
    def __init__(self):
        self.subsystem_template_dir = "subsystem"
        self.common_rdl_f = os.path.join(os.path.dirname(__file__), "rdl", "common.rdl")

        # self.subsystem = Subsystem()

    def list_files(self,
            nodes: 'Union[Node, List[Node]]',
            outdir : str,
            ):

        top = self.get_top(nodes)
        walker = RDLWalker(unroll=True)
        listener = SubsystemListener()
        walker.walk(top, listener)
        subsystems = listener.subsystem_nodes

        out_files = [os.path.join(outdir, getOrigTypeName(s) + ".v") for s in subsystems] # TODO make sure name is correct
        print(*out_files) # Print files to stdout

    def compile_buses(self,
            b_files : List[str],
            ):
        rdlc = RDLCompiler()

        buses = []
        try:
            rdlc.compile_file(self.common_rdl_f)
            for input_file in b_files:
                rdlc.compile_file(input_file)
                try:
                    root = rdlc.elaborate()
                    for top in root.children():
                        buses.append(top)
                        top = top

                except RDLCompileError:
                    pass
        except RDLCompileError:
            sys.exit(1)

        return rdlc

    def get_top(self,
            nodes: 'Union[Node, List[Node]]',
            ):
        # if not a list
        if not isinstance(nodes, list):
            nodes = [nodes]

        for i, node in enumerate(nodes):
            if isinstance(node, RootNode):
                nodes[i] = node.top

        return nodes[0] # TODO


    def export(self,
            nodes: 'Union[Node, List[Node]]',
            outdir: str, 
            buses: 'List[str]',
            list_files: bool=False,
            **kwargs: 'Dict[str, Any]') -> None:

        # if not a list
        top = self.get_top(nodes)


        if kwargs:
            raise TypeError("got an unexpected keyword argument '%s'" % list(kwargs.keys())[0])

        try:
            os.makedirs(outdir)
        except FileExistsError:
            pass


        bus_rdlc = self.compile_buses(buses)

        walker = RDLWalker(unroll=True)
        listener = SubsystemListener()
        walker.walk(top, listener)
        subsystems = [Subsystem(x, bus_rdlc) for x in listener.subsystem_nodes]


        for subsys in subsystems:
            context = {
                    'subsys' : subsys 
                    }
            text = self.process_template(context, "subsystem.j2", subsys)

            out_file = os.path.join(outdir, subsys.getName(subsys.root) + ".v")
            with open(out_file, 'w') as f:
                f.write(text)

    def process_template(self, context : dict, template : str, subsys : Subsystem) -> str:

        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader('%s/subsystem/' % os.path.dirname(__file__)),
            trim_blocks=True,
            lstrip_blocks=True)

        env.filters.update({
            'zip' : zip,
            'int' : int,
            'getName' : subsys.getName,
            'getSlaves' : subsys.getSlaves,
            'getNumEndpoints' : subsys.getNumEndpoints,
            'getBusSignals' : subsys.getBusSignals,
            'getParameters' : subsys.getParameters,
            'getSignals' : subsys.getSignals,
            })

        res = env.get_template(template).render(context)
        return res

