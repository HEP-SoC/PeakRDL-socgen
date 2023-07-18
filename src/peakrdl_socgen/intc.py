from systemrdl import RDLCompiler
from systemrdl.node import AddrmapNode
from systemrdl.rdltypes.array import ArrayPlaceholder
from systemrdl.rdltypes.user_struct import UserStruct
from typing import List
import math

from .module import Module
from .intf import Intf, IntfPort, Modport
from .signal import Signal

class IntcBase:
    def __init__(self, 
            type_name : str,
            intf_type_name : str,
            ):
        self.intc_type_name = type_name
        self.intf_type_name = intf_type_name

class Intc(Module):
    def __init__(self,
            rdlc : RDLCompiler,
            ext_slv_ports : List[Intf],
            ext_mst_ports : List[Intf],
            subsystem_node : "Subsystem", # type: ignore
            inst_prefix : str="",
            ):
        self.rdlc = rdlc
        self.ext_slv_ports = ext_slv_ports
        self.ext_mst_ports = ext_mst_ports
        self.subsystem_node = subsystem_node
        self.inst_prefix = inst_prefix

        self.intf_type = ext_slv_ports[0].type
        self.type_name = ext_slv_ports[0].type.replace("_intf_node", "_interconnect")

        all_ports = [*self.ext_slv_ports, *self.ext_mst_ports]
        same_intf = all(x.type == all_ports[0].type for x in all_ports)
        assert same_intf, f"All interfaces to interconnect must be same type, {[ intf.type for intf in all_ports ]}"

        self.node = self.create_intc_node()

        self.get_intfs()

        super().__init__(self.node, self.rdlc)


    def isDriver(self, s : Signal, intf : Intf):
        if intf in self.ext_slv_ports:
            if s.isOnlyMiso():
                return True
            elif s.isOnlyMosi():
                return False

        if intf in self.ext_mst_ports:
            if s.isOnlyMiso():
                return False
            elif s.isOnlyMosi():
                return True

        assert False, f"Interface is not connected to interconnect {intf.module.node.inst_name}_{intf.sig_prefix}{intf.name}"

    def create_intc_node(self) -> AddrmapNode:

        intc_name = self.type_name

        param_values = {
                'N_MST_PORTS'   : len(self.ext_mst_ports),
                }

        for p in self.ext_slv_ports[0].params._values:
            if isinstance(self.ext_slv_ports[0].params.__getattr__(p), int) and not isinstance(self.ext_slv_ports[0].params.__getattr__(p), bool):
                param_values[p] = self.ext_slv_ports[0].params.__getattr__(p)

        if len(self.ext_slv_ports) > 1:
            param_values['N_SLV_PORTS'] = len(self.ext_slv_ports)

        mmap_params = self.get_intc_mmap_type(intc_name)
        if mmap_params is not None:
            param_values.update(mmap_params)

        root = self.rdlc.elaborate(
                top_def_name=intc_name,
                inst_name=self.inst_prefix + intc_name + "_i",
                parameters = param_values,
                )
        new_intc = root.find_by_path(self.inst_prefix + intc_name + "_i")


        return new_intc # type: ignore

    def round_up_to_pwr2(self, num):
        return int(math.pow(2, math.ceil(math.log2(num))))

    def get_intc_mmap_type(self, intc_name : str): 
        self.getSlaveNodes()
        dflt_intc = self.rdlc.elaborate(
                top_def_name=intc_name,
                inst_name="default_" + intc_name,
                ).get_child_by_name("default_" + intc_name)
        assert dflt_intc is not None

        params = {}
        for p in dflt_intc.inst.parameters:
            # MEM_MAP scheme, array of START, END adresses
            if p.name == "MEM_MAP" and isinstance(p.param_type, ArrayPlaceholder):
                if p.param_type.element_type == int:
                    params['MEM_MAP'] = []
                    for c in self.getSlaveNodes():
                        params['MEM_MAP'].extend([c.absolute_address, c.absolute_address + c.size])

            # SLAVE_ADDR, SLAVE_MASK scheme
            if p.name == "SLAVE_ADDR" and isinstance(p.param_type, ArrayPlaceholder):
                if p.param_type.element_type == int:
                    params['SLAVE_ADDR'] = []
                    for c in reversed(self.getSlaveNodes()):
                        params['SLAVE_ADDR'].append(c.absolute_address)

            if p.name == "SLAVE_MASK" and isinstance(p.param_type, ArrayPlaceholder):
                if p.param_type.element_type == int:
                    params['SLAVE_MASK'] = []
                    for c in reversed(self.getSlaveNodes()):
                        mask = self.fillOnesFromLeft(self.round_up_to_pwr2(c.size), 32) # TODO width
                        params['SLAVE_MASK'].append(mask)

        return params

    def getSlaveNodes(self):
        return [intf.orig_intf.module.node for intf  in self.ext_mst_ports] # type:ignore

    def fillOnesFromLeft(self, num, width):
        ret = 0
        for i in reversed(range(0, width)):
            if num & (1<<i) == 0:
                ret = ret |  1<<i
            else:
                return ret | num

    def getIntcParams(self):
        max_dataw = max([*self.ext_slv_ports, *self.ext_mst_ports], key=lambda intf: intf.data_width).data_width
        max_addrw = max([*self.ext_slv_ports, *self.ext_mst_ports], key=lambda intf: intf.addr_width).addr_width

        return {'data_w': max_dataw, 'addr_w': max_addrw}

    def get_intfs(self):
        intfs = []
        for c in self.getAddrmaps():
            dim = 1
            if c.is_array:
                dim = c.array_dimensions[0]

            for i in range(dim):
                intfs.append(IntfPort(
                        rdlc=self.rdlc,
                        port_node=c,
                        module=self,
                        orig_intf=None,
                        idx = i,
                        in_array = dim > 1,
                        )
                     )
                if intfs[-1].params.modport.name == "slave":
                    intfs[-1].orig_intf = self.ext_slv_ports[i]
                else:
                    intfs[-1].orig_intf = self.ext_mst_ports[i]

        return intfs

    def getSlavePorts(self): # TODO use the one from module
        return [intf for intf in self.get_intfs() if intf.modport.name == "slave"]

    def getMasterPorts(self): # TODO use the one from module
        return [intf for intf in self.get_intfs() if intf.modport.name == "master"]
