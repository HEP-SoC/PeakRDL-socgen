from systemrdl import RDLCompiler
from systemrdl.node import AddrmapNode
from systemrdl.rdltypes.array import ArrayedType
from typing import List, Dict, TYPE_CHECKING
import math

from .module import Module
from .intf import IntfPort

class Intc(Module):
    """Module class extension for interconnect modules."""
    def __init__(self,
            rdlc: RDLCompiler,
            ext_slv_ports: List[IntfPort],
            ext_mst_ports: List[IntfPort],
            subsystem_node: AddrmapNode,
            inst_prefix: str="",
            ):
        self.rdlc = rdlc
        # List of slave/master interface ports making the interconnect
        self.ext_slv_ports = ext_slv_ports
        # !!! The master list may contain ports with modport = 'slave' because
        # of adapter integration. Don't filter on modport for these ports !!!
        self.ext_mst_ports = ext_mst_ports

        # Interconnect name prefix
        self.inst_prefix = inst_prefix

        # Parent subsystem node
        self.subsystem_node = subsystem_node

        # At that point all ports must have the same type
        self.intf_type = ext_slv_ports[0].type
        # Every intf_node must have a corresponding interconnect version corresponding to a verilog module
        self.type_name = ext_slv_ports[0].type.replace("_intf_node", "_interconnect")

        # Instance name using prefix + base name
        self.inst_name = self.inst_prefix + self.type_name

        all_ports = [*self.ext_slv_ports, *self.ext_mst_ports]
        same_intf = all(x.type == all_ports[0].type for x in all_ports)
        assert same_intf, f"All interfaces to interconnect must be same type, {[ intf.type for intf in all_ports ]}"

        self.node = self.create_intc_node()

        super().__init__(self.node, self.rdlc)

    @property
    def num_ext_slaves(self) -> int:
        """Return the number of slave ports."""
        n_ports = len(self.ext_slv_ports)
        assert n_ports > 0, f'Subsystem {self.subsystem_node.inst_name} has not external slave.'
        return n_ports

    @property
    def num_ext_masters(self) -> int:
        """Return the number of master ports."""
        n_ports = len(self.ext_mst_ports)
        assert n_ports > 0, f'Subsystem {self.subsystem_node.inst_name} has not external master.'
        return n_ports

    def create_intc_node(self) -> AddrmapNode:
        """Generates the corresponding AddrmapNode from the interconnect parameters."""
        intc_name = self.type_name

        # Set the number of masters
        param_values = {'N_MST_PORTS': len(self.ext_mst_ports)}
        # Extract all the integer parameters
        for p in self.ext_slv_ports[0].params._values:
            attr_val = self.ext_slv_ports[0].params.__getattr__(p)
            if isinstance(attr_val, int) and not isinstance(attr_val, bool):
                param_values[p] = self.ext_slv_ports[0].params.__getattr__(p)

        if len(self.ext_slv_ports) > 1:
            param_values['N_SLV_PORTS'] = len(self.ext_slv_ports)

        mmap_params = self.get_intc_mmap_params(intc_name)
        if mmap_params is not None:
            param_values.update(mmap_params)

        root = self.rdlc.elaborate(
                top_def_name=intc_name,
                inst_name=self.inst_name,
                parameters = param_values,
                )
        new_intc = root.find_by_path(self.inst_name)

        return new_intc

    def _round_up_to_pwr2(self, num):
        """Returns the value rounded up to the next power of 2."""
        return int(math.pow(2, math.ceil(math.log2(num))))

    def get_intc_mmap_params(self, intc_name: str) -> Dict:
        """Generates the address map parameters of the interconnect."""
        # Get the default interconnect module definition from the interface SystemRDL compiler
        dflt_intc = self.rdlc.elaborate(
                top_def_name=intc_name,
                inst_name="default_" + intc_name,
                ).get_child_by_name("default_" + intc_name)
        assert dflt_intc is not None

        params = {}
        for p in dflt_intc.inst.parameters:
            # MEM_MAP scheme, array of START, END adresses
            if p.name == "MEM_MAP" and isinstance(p.param_type, ArrayedType):
                if p.param_type.element_type == int:
                    params['MEM_MAP'] = []
                    for c in self._getSlaveNodes():
                        params['MEM_MAP'].extend([c.absolute_address, c.absolute_address + c.size])

            # SLAVE_ADDR, SLAVE_MASK scheme
            elif p.name == "SLAVE_ADDR" and isinstance(p.param_type, ArrayedType):
                if p.param_type.element_type == int:
                    params['SLAVE_ADDR'] = []
                    for c in reversed(self._getSlaveNodes()):
                        params['SLAVE_ADDR'].append(c.absolute_address)

            elif p.name == "SLAVE_MASK" and isinstance(p.param_type, ArrayedType):
                if p.param_type.element_type == int:
                    params['SLAVE_MASK'] = []
                    for c in reversed(self._getSlaveNodes()):
                        mask = self._fillOnesFromLeft(self._round_up_to_pwr2(c.size), 32) # TODO width
                        params['SLAVE_MASK'].append(mask)

            elif p.name == "SOCGEN_XBAR_ADDR_RULES":# and isinstance(p.param_type, str): # TODO why not working
                sv_intc_prefix = self.inst_name.replace("interconnect", "intc").upper() + "_ADDR_RULES"
                params['SOCGEN_XBAR_ADDR_RULES'] = sv_intc_prefix

        return params

    def _getSlaveNodes(self) -> List[IntfPort]:
        """TBD"""
        return [intf.orig_intf.module.node for intf in self.ext_mst_ports]

    def _fillOnesFromLeft(self, num, width):
        """Set to one the bits to the left of the most left bit to one up to width number of bits.
        Example: num=1024 (0x400) and width=32 -> filled=4294966272 (0xFFFFFC00)
        """
        ret = 0
        for i in reversed(range(0, width)):
            if num & (1<<i) == 0:
                ret = ret | 1<<i
            else:
                return ret | num
