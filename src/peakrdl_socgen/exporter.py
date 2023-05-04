from typing import  Dict, Any
from systemrdl import  AddrmapNode, RDLCompiler, RDLWalker
from systemrdl.node import  Node, RootNode
from typing import List, Union
import os
import jinja2

from .subsystem import Subsystem, SubsystemListener, getOrigTypeName

class SocExporter():
    def __init__(self):
        self.subsystem_template_dir = "subsystem"
        self.common_rdl_f = os.path.join(os.path.dirname(__file__), "rdl", "common.rdl")
        self.intc_wrap_rdl_f = os.path.join(os.path.dirname(__file__), "rdl", "interconnect_wrap.rdl")

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
        out_files += [os.path.join(outdir, getOrigTypeName(s) + "_intc_wrap.v") for s in subsystems] # TODO make sure name is correct
        for subs in subsystems:
            assert isinstance(subs, AddrmapNode)
            for intcw in subs.get_property("intcw_l", default=[]):
                out_files += [os.path.join(outdir, intcw.name + "_intc_wrap.v")]


        print(*out_files) # Print files to stdout

    def compile_glue(self,
            b_files : List[str],
            ):
        rdlc = RDLCompiler()
        rdlc.compile_file(self.common_rdl_f)
        rdlc.compile_file(self.intc_wrap_rdl_f)
        for input_file in b_files:
            rdlc.compile_file(input_file)
            root = rdlc.elaborate()
            for top in root.children():
                top = top
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
            intfs: 'List[str]',
            **kwargs: 'Dict[str, Any]') -> None:

        # if not a list
        top = self.get_top(nodes)


        if kwargs:
            raise TypeError("got an unexpected keyword argument '%s'" % list(kwargs.keys())[0])

        try:
            os.makedirs(outdir)
        except FileExistsError:
            pass


        rdlc = self.compile_glue(intfs)

        walker = RDLWalker(unroll=True)
        listener = SubsystemListener()
        walker.walk(top, listener)
        # subsystems = [Subsystem(x, rdlc) for x in listener.subsystem_nodes]
        subsystems = [Subsystem(x, rdlc) for x in listener.subsystem_nodes]


        for subsys in subsystems:
            context = {
                    'subsys' : subsys 
                    }
            text = self.process_template(context, "subsystem.j2")

            out_file = os.path.join(outdir, subsys.getName() + ".v")
            with open(out_file, 'w') as f:
                f.write(text)

        for subsys in subsystems:
            for intcw in subsys.intc_wraps:
                context = {
                        'intcw' : intcw 
                        }
                text = self.process_template(context, "intc_wrap.j2")

                out_file = os.path.join(outdir, intcw.getOrigTypeName() + ".v")
                with open(out_file, 'w') as f:
                    f.write(text)

            # text = self.process_dot_template({'subsys': subsystems[0]})

            # out_file = os.path.join(outdir, subsystems[0].node.inst_name + ".dot")
            # with open(out_file, 'w') as f:
            #     f.write(text)

    def process_template(self, context : dict, template : str) -> str:

        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader('%s/subsystem/' % os.path.dirname(__file__)),
            trim_blocks=True,
            lstrip_blocks=True)

        env.filters.update({
            'zip' : zip,
            'int' : int,
            })

        res = env.get_template(template).render(context)
        return res

    def process_dot_template(self, context : dict) -> str:

        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader('%s/dot/' % os.path.dirname(__file__)),
            trim_blocks=True,
            lstrip_blocks=True)

        env.filters.update({
            'zip' : zip,
            'int' : int,
            })

        res = env.get_template('dot.j2').render(context)
        return res

