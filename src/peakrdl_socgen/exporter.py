from typing import  Dict, Any
from systemrdl import  AddrmapNode, RDLCompiler, RDLWalker
from systemrdl.node import  Node, RootNode
from typing import List, Union
import os
import jinja2

from .subsystem import Subsystem, SubsystemListener, getOrigTypeName

def dot_to_uscore(in_str):
    return in_str.replace(".", "_")

def get_file_content(file : str) -> str:
    ret_str = ""
    with open(file, "r") as f:
        ret_str = f.read()
    return ret_str

def get_file_name(file : str) -> str:
    return os.path.basename(file)

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

    def compile_glue(self,
            b_files : List[str],
            ):
        rdlc = RDLCompiler()
        rdlc.compile_file(self.common_rdl_f)
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
            vinject : 'List[str]',
            use_include : bool = False,
            gen_dot : bool = False,
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
            subsys_inj_files = []
            for inj_f in vinject:
                if os.path.basename(inj_f).startswith(subsys.getOrigTypeName()):
                    subsys_inj_files.append(inj_f)
            context = {
                    'subsys' : subsys,
                    'inj_f'  : subsys_inj_files,
                    'use_include' : use_include,
                    }
            text = self.process_template(context, "subsystem.j2")

            out_file = os.path.join(outdir, subsys.getOrigTypeName() + ".v")
            with open(out_file, 'w') as f:
                f.write(text)

        if gen_dot:
            context = {
                    'subsystems' : subsystems 
                    }
            text = self.process_dot_template(context)

            out_file = os.path.join(outdir, "soc_diagram.dot")
            with open(out_file, 'w') as f:
                f.write(text)

    def process_template(self, context : dict, template : str) -> str:

        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader('%s/subsystem/' % os.path.dirname(__file__)),
            trim_blocks=True,
            lstrip_blocks=True)

        env.filters.update({
            'zip' : zip,
            'int' : int,
            'path_conv' : dot_to_uscore,
            'get_file_content' : get_file_content,
            'get_file_name' : get_file_name,
            })

        res = env.get_template(template).render(context)
        return res

    def process_dot_template(self, context : dict) -> str:

        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader('%s/dot/' % os.path.dirname(__file__)),
            trim_blocks=True,
            extensions=['jinja2.ext.loopcontrols'],
            lstrip_blocks=True)

        env.filters.update({
            'zip' : zip,
            'int' : int,
            'path_conv' : dot_to_uscore,
            })

        res = env.get_template('dot.j2').render(context)
        return res

