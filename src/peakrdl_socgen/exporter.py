from systemrdl.node import  Node, RootNode, AddrmapNode
from typing import List, Union
import os
import shutil
import jinja2

from .subsystem import Subsystem

class SocExporter():
    def __init__(self):
        self.subsystem_template_dir = "subsystem"

        # self.subsystem = Subsystem()



    def export(self,
            nodes: 'Union[Node, List[Node]]',
            outdir: str, 
            list_files: bool=False,
            ext : list=[],
            **kwargs: 'Dict[str, Any]') -> None:


        # if not a list
        if not isinstance(nodes, list):
            nodes = [nodes]

        # If it is the root node, skip to top addrmap
        for i, node in enumerate(nodes):
            if isinstance(node, RootNode):
                nodes[i] = node.top

        if kwargs:
            raise TypeError("got an unexpected keyword argument '%s'" % list(kwargs.keys())[0])

        try:
            os.makedirs(outdir)
        except FileExistsError:
            pass

        for node in nodes:
            subsys = Subsystem(node)
            context = {
                    'subsys' : subsys 
                    }
            text = self.process_template(context, "subsystem.j2", subsys)

            out_file = os.path.join(outdir, subsys.getName(node) + ".v")
            with open(out_file, 'w') as f:
                f.write(text)

    def process_template(self, context : dict, template : str, subsys : Subsystem) -> str:

        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader('%s/subsystem/' % os.path.dirname(__file__)),
            trim_blocks=True,
            lstrip_blocks=True)

        env.filters.update({
            'zip' : zip,
            'getName' : subsys.getName,
            'getSlaves' : subsys.getSlaves,
            'getNumEndpoints' : subsys.getNumEndpoints,
            'getBusSignals' : subsys.getBusSignals,
            'getParameters' : subsys.getParameters,
            'getSignals' : subsys.getSignals,
            })

        res = env.get_template(template).render(context)
        return res

