from systemrdl import RDLCompiler
from typing import Dict, OrderedDict, Any
from systemrdl.node import AddrmapNode, Node
from systemrdl.rdltypes.user_struct import UserStruct
from systemrdl.rdltypes.user_enum import UserEnum
from enum import Enum

from .signal import IntfSignal, Signal

class Modport(Enum):  # TODO make it same type as the RDL one
    slave = 0
    master = 1

class IntfPort:

    def __init__(self,
                 rdlc        : RDLCompiler,
                 port_node   : AddrmapNode,
                 module      : "Module",
                 orig_intf   : "IntfPort|None"=None,
                 idx         : int = 0,
                 in_array    : bool = False,
                 ):
        self.rdlc = rdlc
        self.node = port_node
        self.module = module
        self.idx = idx
        self.in_array = in_array

        self.orig_intf = orig_intf
        if orig_intf is None:
            self.orig_intf = self

        if self.node.is_array:
            assert len(self.node.array_dimensions) <= 1, f"Array dimension of {port_node} more than 1, {self.node.array_dimensions}"
        self.arr_dim = self.node.array_dimensions[0] if self.node.is_array else 1

        for k in self.params._values:
            setattr(self, k, self.params._values[k])

        self.type = self.node.orig_type_name

        self.signals = self.createSignals()

    @property
    def params(self) -> UserStruct:
        intf_inst = self.node.get_property('intf_inst', default=None)
        assert intf_inst is not None, f"No intf_inst defined for interface node: {self.node.orig_type_name}"
        return intf_inst

    def createSignals(self):
        signals = []
        for s in self.node.signals():
            signals.append(IntfSignal(s, self))
        return signals

    # def __getattr__(self, name: str) -> Any:
        # assert False, f"Parameter {name} not in {self.node.orig_type_name}, {self.params._values}"

    def __str__(self) -> str:
        ret_s = "Interface: " + str(self.type) + ", module: " + self.module.node.get_path() + ", "
        for a in self.params._values:
            ret_s += a + ": " + str(self.params.__getattr__(a)) + ", "

        assert(self.signals is not None)
        for s in self.signals:
            ret_s += "\n        " + str(s)

        return ret_s

    def findSignal(self, sig : Signal) -> IntfSignal:
        signals = [s for s in self.signals if s.basename == sig.basename]
        assert len(signals) == 1, f"Looking for {sig.basename}, exactly one element with the same basename must exist found: {len(signals)} {signals}"
        return signals[0]

    def getXdotName(self):
        if self.in_array:
            return self.prefix + f"{self.idx}"
        else:
            return self.prefix

class Intf:
    def __init__(self,
            intf_node : AddrmapNode,
            parent_node : AddrmapNode,
            rdlc : RDLCompiler,
            sig_prefix : str = "",
            orig_intf : "Intf|None" = None,
            capitalize : bool = False,
            N : int=1,
            ):
        self.node = intf_node
        self.rdlc = rdlc

        prop = self.node.get_property("intf_inst")

        self.name = prop.name
        self.sig_prefix = sig_prefix
        self.capitalize = capitalize

        self.addr_width = prop.ADDR_WIDTH
        self.data_width = prop.DATA_WIDTH
        self.module = module
        self.__orig_intf = orig_intf
        self.N = N

        self.signals = self.getSignals(self.node, self.sig_prefix)

    @property
    def orig_intf(self):
        return self if self.__orig_intf is None else self.__orig_intf

    @orig_intf.setter
    def orig_intf(self, value):
        self.__orig_intf = value

    # @property
    # def isMaster(self):
    #     return self.modport == Modport.master
    #
    # @property
    # def isSlave(self):
    #     return self.modport == Modport.slave

    def getSignals(self, intf_node : AddrmapNode, prefix : str = ""):
        signals = []
        if self.isIntf(intf_node):
            for s in intf_node.signals():
                signals.append(IntfSignal(s, prefix, capitalize=self.capitalize))
        return signals

    def findSignal(self, basename : str) -> IntfSignal:
        signals = [s for s in self.signals if s.basename == basename]
        assert len(signals) == 1, f"Looking for {basename}, exactly one element with the same basename must exist found: {len(signals)} {signals}"
        return signals[0]

    # def getSignalVerilogType(self, sig : Signal):
    #     if sig.bidir:
    #         return "inout"
    #
    #     if sig.miso and not sig.mosi:
    #         if self.modport == Modport.slave:
    #             return "output wire"
    #         elif self.modport == Modport.master:
    #             return "input wire"
    #     elif sig.mosi and not sig.miso:
    #         if self.modport == Modport.slave:
    #             return "input wire"
    #         elif self.modport == Modport.master:
    #             return "output wire"
    #
    #     return "ERROR BUG FOUND"

    def getSlavePrefix(self, intf : "Intf") -> str:
        if intf.sig_prefix == "":
            return "s_"
        else:
            return intf.sig_prefix

    def getOrigTypeName(self, node : AddrmapNode) -> str: # TODO Move to common
        if node.orig_type_name is not None:
            return node.orig_type_name
        else:
            return node.inst_name

    def getAddrWidth(self):
        if self.node.get_property("ADDR_WIDTH"):
            pass

    def getParameters(self, node : AddrmapNode): # TODO Move to common
        params = []
        for p in node.inst.parameters:
            params.append(p)

        return params
    
    def getParam(self, node : AddrmapNode,  name : str): # TODO Move to common
        for p in node.inst.parameters:
            if name == p.name:
                return p

        # TODO THROW EXCEPTION
        return None

    def getParamValue(self, node : AddrmapNode, name : str):
        param = self.getParam(node, name)
        if param is not None:
            return param.get_value()
        # TODO THROW EXCEPTION

    def isIntf(self, node : Node ): # TODO move to common
        if not isinstance(node, AddrmapNode):
            return False
        if node.get_property("intf") is not None:
            return True 
        return False 

    def isAdapterNeeded(self, first : "Intf", second : "Intf"):
        if first.name == second.name:
            return False
        else:
            return True

    def print(self):
        print("Printing")
        print("Intf: ", self.name,
                " Parent node: ", self.module.get_path(),
                " Prefix: ", self.sig_prefix,
                " Addr width: ", self.addr_width,
                " Data width: ", self.data_width
                )
        assert(self.signals is not None)
        for s in self.signals:
            s.print()

    # Turn master into slave and change parent
    def mirror_intf(self,
            new_parent : AddrmapNode,
            ):

        modport = None
        if self.modport == Modport.slave:
            modport = Modport.master
        elif self.modport == Modport.master:
            modport = Modport.slave
        assert modport is not None

        return create_intf(
                self.rdlc, 
                new_parent, 
                intf_type=self.name,
                addr_width=self.addr_width,
                data_width=self.data_width,
                prefix="new_",
                modport=modport,
                N=self.N,
                )


def get_intf_param_string(
        intf_type : str,
        intf_dict : "Dict"
        ):

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

def create_intf_port(
        rdlc,
        module : "Module",
        intf_struct,
        orig_intf  : "Intf|None" = None,
        N : int=1,
        ):

    intf_type = intf_struct.__class__.__qualname__
    intf_type_str = get_intf_param_string(
            intf_type=intf_type,
            intf_dict=intf_struct._values,
            )
    
    param = rdlc.eval(intf_type_str)

    intf_node_name = intf_type + "_node"
    new_port_root = rdlc.elaborate(
            top_def_name=intf_node_name,
            inst_name=intf_node_name,
            parameters={'INTF': param}
            )
    new_port = new_port_root.get_child_by_name(intf_node_name)
    assert(isinstance(new_port, AddrmapNode))

    return IntfPort(
            rdlc=rdlc,
            port_node=new_port,
            module=module
            )
    
    # return Intf(
    #         intf_node=new_intf,
    #         module=module,
    #         rdlc=rdlc,
    #         sig_prefix=prefix,
    #         modport=list(Modport)[modport.value],
    #         capitalize=capitalize,
    #         N=N,

    #         orig_intf=orig_intf)
