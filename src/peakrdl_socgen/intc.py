from systemrdl import RDLCompiler
from systemrdl.node import AddrmapNode
from systemrdl.rdltypes.array import ArrayPlaceholder
from typing import List
import math

from .module import Module
from .intf import Intf, IntfModport
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
            ext_slv_intfs : List[Intf],
            ext_mst_intfs : List[Intf],
            subsystem_node : "Subsystem", # type: ignore
            ):
        self.rdlc = rdlc
        self.ext_slv_intfs = ext_slv_intfs
        self.ext_mst_intfs = ext_mst_intfs
        self.subsystem_node = subsystem_node

        self.intf_type_name = ext_slv_intfs[0].name
        self.type_name = ext_slv_intfs[0].name.replace("_intf", "_interconnect")

        all_ports = [*self.ext_slv_intfs, *self.ext_mst_intfs]
        same_intf = all(x.name == all_ports[0].name for x in all_ports)
        assert same_intf, f"All interfaces to interconnect must be same type, {[ intf.name for intf in all_ports ]}"

        self.node = self.create_intc_node()

        super().__init__(self.node, self.rdlc)

        # for i in self.ext_slv_intfs:
        #     i.print()

    # def get_intfs(self):
    #     return [self.getSlaveIntf(), self.getMasterIntf()]

    def isDriver(self, s : Signal, intf : Intf):
        if intf in self.ext_slv_intfs:
            if s.isOnlyMiso():
                return True
            elif s.isOnlyMosi():
                return False

        if intf in self.ext_mst_intfs:
            if s.isOnlyMiso():
                return False
            elif s.isOnlyMosi():
                return True

        assert False, f"Interface is not connected to interconnect {intf.parent_node.inst_name}_{intf.sig_prefix}{intf.name}"

    def create_intc_node(self) -> AddrmapNode:

        intc_params = self.getIntcParams()
        intc_name = self.type_name

        param_values = {
                'N_SLAVES'   : len(self.ext_slv_intfs),
                'DATA_WIDTH' : max(intc_params['data_w'], intc_params['data_w']),
                'ADDR_WIDTH' : max(intc_params['addr_w'], intc_params['addr_w']),
                }
        if len(self.ext_slv_intfs) > 1:
            param_values['N_MASTERS'] = len(self.ext_mst_intfs)

        mmap_params = self.get_intc_mmap_type(intc_name)
        if mmap_params is not None:
            param_values.update(mmap_params)

        root = self.rdlc.elaborate(
                top_def_name=intc_name,
                inst_name=intc_name + "_i",
                parameters = param_values,
                )
        new_intc = root.find_by_path(intc_name + "_i")


        return new_intc # type: ignore

    def round_up_to_pwr2(self, num):
        return int(math.pow(2, math.ceil(math.log2(num))))

    def get_intc_mmap_type(self, intc_name : str): 
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
                    for c in self.subsystem_node.getSlaveNodes():
                        params['MEM_MAP'].extend([c.absolute_address, c.absolute_address + c.size])

            # SLAVE_ADDR, SLAVE_MASK scheme
            if p.name == "SLAVE_ADDR" and isinstance(p.param_type, ArrayPlaceholder):
                if p.param_type.element_type == int:
                    params['SLAVE_ADDR'] = []
                    for c in reversed(self.subsystem_node.getSlaveNodes()):
                        params['SLAVE_ADDR'].append(c.absolute_address)

            if p.name == "SLAVE_MASK" and isinstance(p.param_type, ArrayPlaceholder):
                if p.param_type.element_type == int:
                    params['SLAVE_MASK'] = []
                    for c in reversed(self.subsystem_node.getSlaveNodes()):
                        mask = self.fillOnesFromLeft(self.round_up_to_pwr2(c.size), 32) # TODO width
                        params['SLAVE_MASK'].append(mask)

        return params

    def fillOnesFromLeft(self, num, width):
        ret = 0
        for i in reversed(range(0, width)):
            if num & (1<<i) == 0:
                ret = ret |  1<<i
            else:
                return ret | num

    def getIntcParams(self):
        max_dataw = max([*self.ext_slv_intfs, *self.ext_mst_intfs], key=lambda intf: intf.data_width).data_width
        max_addrw = max([*self.ext_slv_intfs, *self.ext_mst_intfs], key=lambda intf: intf.addr_width).addr_width

        return {'data_w': max_dataw, 'addr_w': max_addrw}

    def get_intfs(self):
        intfs = []
        for c in self.getAddrmaps():
            if c.get_property("intf"):
                intf_inst = c.get_property("intf_inst")
                N = c.get_property("n_array")
                try:
                    cap = intf_inst.cap
                except:
                    cap = False

                intf = Intf(c,
                            self.node,
                            self.rdlc,
                            sig_prefix=intf_inst.prefix,
                            modport=list(IntfModport)[intf_inst.modport.value],
                            N=N,
                            capitalize=cap,
                            )
                intfs.append(intf)
        return intfs

    def getSlaveIntf(self):
        return [intf for intf in self.intfs if intf.modport == IntfModport.SLAVE]

    def getMasterIntf(self):
        return [intf for intf in self.intfs if intf.modport == IntfModport.MASTER]
