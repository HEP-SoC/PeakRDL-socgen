from typing import TYPE_CHECKING, Dict, Optional, List
from systemrdl import RDLCompiler
from systemrdl.node import AddrmapNode
from systemrdl.rdltypes.user_struct import UserStruct
from systemrdl.rdltypes.user_enum import UserEnum
from enum import Enum

from .signal import IntfSignal, Signal

if TYPE_CHECKING:
    from .module import Module

class Modport(Enum): # TODO make it same type as the RDL one
    slave = 0
    master = 1

class IntfPort:
    """Wrapper arround an AddrmapNode used to represent an interface node/port that needs to be connected to a bus.

    An interface port is described by a <type>_intf_node addrmap, e.g., apb_intf_node. Every interface should follow
    this format:

        addrmap <type>_intf_node #(
            <type>_intf INTF = <type>_intf '{
                                    ADDR_WIDTH:32,
                                    DATA_WIDTH:32,
                                    ...}
        ){
            intf;
            intf_inst = INTF;  // property of type base_intf

            // Interface signal declaration
            ...
        };
    """
    def __init__(self,
                 port_node: AddrmapNode,
                 module: 'Module',
                 orig_intf: Optional['IntfPort'] = None,
                 idx: int = 0
                 ):
        self.node = port_node
        self.module = module
        self.idx = idx

        self.orig_intf = orig_intf
        if orig_intf is None:
            self.orig_intf = self

        # Iterate over the intf structure and set the attribute to the class object
        # Example of an apb intf structure:
        # apb_intf'{
        #     ADDR_WIDTH:32,
        #     DATA_WIDTH:32,
        #     prefix:"s_",
        #     modport:Modport::slave,
        #     cap:false,
        #     // Regex property
        #     // each \ character must be escaped twice to get "([ABC])_([io])$::_\2\1"
        #     // applied by the regex python code:
        #     // 1. systemrdl compiler removes the first escape \
        #     // 2. eval call from peakrdl-socgen removes the second one
        #     // This is used to have compatiblity between peakrdl-socgen using _i/o/io format
        #     // and tmrg appending blindly A/B/C to input/ouput TMR signals
        #     // Example: obi_reqA_i --> obi_req_iA
        #     regex:"match_pattern::replace_pattern"
        # }
        for k in self.params._values:
            setattr(self, k, self.params._values[k])

        self.type = self.node.orig_type_name

        self.signals = self.createSignals()

    @property
    def params(self) -> UserStruct:
        """Gets the intf port parameters."""
        # This is a mandatory property for every interface node (see the example above).
        intf_inst = self.node.get_property('intf_inst', default=None)
        assert intf_inst is not None, f"No intf_inst defined for interface node: {self.node.orig_type_name}"
        return intf_inst

    def createSignals(self):
        """Returns a list with the signal composing an interface."""
        signals = []
        for s in self.node.signals():
            signals.append(IntfSignal(s, self))
        return signals

    def __str__(self) -> str:
        """Returns a summary string of the interface parameters and signals."""
        ret_s = f"Interface: {self.type}, module: {self.module.node.get_path()}, "
        # Add the interface parameters
        for a in self.params._values:
            ret_s += a + ": " + str(self.params.__getattr__(a)) + ", "

        assert(self.signals is not None)
        # Add the interface signals
        for s in self.signals:
            ret_s += "\n        " + str(s)

        return ret_s

    def findSignal(self, sig: Signal) -> IntfSignal:
        signals = [s for s in self.signals if s.basename == sig.basename]
        assert len(signals) == 1, f"Looking for {sig.basename}, exactly one element with the same basename must exist found: {len(signals)} {signals}"
        return signals[0]

    def getXdotName(self, test: int=0) -> str:
        """Returns interface port name for Xdot graph."""
        return self.prefix + f"{self.idx}"

    @staticmethod
    def get_intf_param_string(intf_type: str, intf_dict: Dict):
        """Create a parameter string for an interface type that can be evaluated with a SystemRDL compiler instance."""
        intf_type_str = f"{intf_type}'{{" # }}
        for k, v in intf_dict.items():

            if isinstance(v, bool):     # Bool is subclass of int, need to check first
                val_str = f'{v.__str__().lower()}'
            elif isinstance(v, int):
                val_str = v
            elif isinstance(v, str):
                val_str = f'"{v}"'
            elif isinstance(v, UserEnum):
                val_str = f'{v.__class__.__name__}::{v.name}'
            else:
                assert False, f"Unexpected type key: {k} value: {v} for {intf_dict}"

            intf_type_str += f"{k}: {val_str}, "

        return intf_type_str[:-2] + "}" # Delete last comma

    def get_module_name(self):
        """Returns the base module name containing the port interface"""
        # If an adapter has been added skip it until we reach the base module
        if self.module.node.get_property("adapter"):
            return self.module.end_node_name
        else:
            return self.module.node.inst_name

    @staticmethod
    def create_intf_port(rdlc: RDLCompiler, module: 'Module', intf_struct) -> List['IntfPort']:
        """Generate IntfPort object(s) for the given interface structure."""

        # Get the interface struct type which defines the interface parameters.
        intf_type = intf_struct.__class__.__name__

        # Check for N_PORTS param
        if 'N_PORTS' in intf_struct._values:
            n_ports = intf_struct._values.pop('N_PORTS')
            # Remove from the dict as it is only used by this script
            # not by the systemRDL interface node
            intf_type = intf_type.replace('intc', 'intf') # TODO Merge intc and intf
        else:
            # By default generate only one port per interface
            n_ports = 1

        intf_prefix = intf_struct._values['prefix']

        # Get the interface parameters, e.g., the address and data width or the
        # interface mode (i.e., slave or master).
        intf_param_str = IntfPort.get_intf_param_string(intf_type=intf_type, intf_dict=intf_struct._values)
        # Evaluate the RDL parameter expression string and return its compiled value
        params = rdlc.eval(intf_param_str)

        ports = []
        for p_cnt in range(n_ports):
            # Each intf structured as a corresponding addrmap definition the '_node" suffix
            intf_node_name = intf_type + "_node"
            intf_inst_name = intf_prefix + str(p_cnt)
            # Use the interface RDL compiler to generate a port node instance (i.e., an AddrMapNode).
            # The default parameter INTF is overwritten by the instance one
            new_port_root = rdlc.elaborate(top_def_name=intf_node_name,
                                        inst_name=intf_inst_name,
                                        parameters={'INTF': params})
            new_port = new_port_root.get_child_by_name(intf_inst_name)
            # Check the port is an AddrmapNode
            assert(isinstance(new_port, AddrmapNode))

            ports.append(IntfPort(port_node=new_port, module=module, idx=p_cnt))

        # Return an IntfPort object
        return ports
