from systemrdl import RDLWalker, RDLListener
from systemrdl import RDLCompiler, RDLCompileError
from typing import List

import sys
import os
import shutil

class AddrmapListener(RDLListener):
    def __init__(self):
        self.addrmaps = []

    def enter_Mem(self, node):
        id = None
        for p in node.parent.inst.parameters:
            if p.name == 'ID':
                id = p.get_value()
        assert(node.parent is not None)
        addrmap = {
                'path' : node.get_path(),
                'addr' : node.absolute_address,
                'size' : node.size,
                'name' : node.parent.inst_name,
                'id'   : id
                # 'id'
                }
        self.addrmaps.append(addrmap)
        
            # self.subsystems.append(Subsystem(node))      

def generate(rdl_files : List[str], build_dir : str):
# Ignore this. Only needed for this example
    this_dir = os.path.dirname(os.path.realpath(__file__))

    rdlc = RDLCompiler()

    try:
        for input_file in rdl_files:
            rdlc.compile_file(input_file)
        root = rdlc.elaborate()
    except RDLCompileError:
        sys.exit(1)

    top = None
    top_gen = root.children(unroll=True)
    for top in top_gen:
        top = top
    assert(top is not None)

    walker = RDLWalker(unroll=True)
    listener = AddrmapListener()
    walker.walk(top, listener)

    out_s = '#include "addrmap.h"\n\n'
    out_s = out_s + 'std::vector<addrmap> get_addrmaps(){\n'
    out_s = out_s + 'std::vector<addrmap> tmp;\n'
    for a in listener.addrmaps:
        out_s = out_s + f'  tmp.push_back(addrmap({a["addr"]}, {a["size"]}, {a["id"]}, "{a["path"]}"));\n'

    out_s = out_s + '  return tmp;\n'
    out_s = out_s + '}\n'

    
    out_file = os.path.join(build_dir, "mmap.cpp")
    with open(out_file, 'w') as f:
        f.write(out_s)


import sys

def main():
    args = sys.argv[1:]
    build_dir = args[0]
    args = args[1:]
    num_files = len(args)

    files = args
    print("Printing files: ", files)
    generate(files, build_dir)


if __name__ == "__main__":
    main()
