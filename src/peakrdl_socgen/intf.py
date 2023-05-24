from systemrdl import RDLCompiler
from typing import Dict
from systemrdl.node import AddrmapNode, Node
from enum import Enum

from .signal import Signal

class IntfModport(Enum):  # TODO make it same type as the RDL one
    SLAVE = 0
    MASTER = 1

class Intf:
    def __init__(self,
            intf_node : AddrmapNode,
            parent_node : AddrmapNode,
            rdlc : RDLCompiler,
            sig_prefix : str = "",
            orig_intf : "Intf|None" = None,
            modport : IntfModport = IntfModport.SLAVE,
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
        self.modport = modport
        self.parent_node = parent_node
        self.__orig_intf = orig_intf
        self.N = N

        self.signals = self.getSignals(self.node, self.sig_prefix)

    @property
    def orig_intf(self):
        return self if self.__orig_intf is None else self.__orig_intf

    @orig_intf.setter
    def orig_intf(self, value):
        self.__orig_intf = value

    @property
    def isMaster(self):
        return self.modport == IntfModport.MASTER

    @property
    def isSlave(self):
        return self.modport == IntfModport.SLAVE

    def getSignals(self, intf_node : AddrmapNode, prefix : str = ""):
        signals = []
        if self.isIntf(intf_node):
            for s in intf_node.signals():
                signals.append(Signal(s, prefix, capitalize=self.capitalize))
        return signals

    def findSignal(self, basename : str) -> Signal:
        signals = [s for s in self.signals if s.basename == basename]
        assert len(signals) == 1, f"Looking for {basename}, exactly one element with the same basename must exist found: {len(signals)} {signals}"
        return signals[0]

    def getSignalVerilogType(self, sig : Signal):
        if sig.bidir:
            return "inout"

        if sig.miso and not sig.mosi:
            if self.modport == IntfModport.SLAVE:
                return "output wire"
            elif self.modport == IntfModport.MASTER:
                return "input wire"
        elif sig.mosi and not sig.miso:
            if self.modport == IntfModport.SLAVE:
                return "input wire"
            elif self.modport == IntfModport.MASTER:
                return "output wire"

        return "ERROR BUG FOUND"

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
        print("Intf: ", self.name,
                " Parent node: ", self.parent_node.get_path(),
                " Prefix: ", self.sig_prefix,
                " Addr width: ", self.addr_width,
                " Data width: ", self.data_width,
                " Modport: ", self.modport,
                )
        assert(self.signals is not None)
        for s in self.signals:
            s.print()

    # Turn master into slave and change parent
    def mirror_intf(self,
            new_parent : AddrmapNode,
            ):

        modport = None
        if self.modport == IntfModport.SLAVE:
            modport = IntfModport.MASTER
        elif self.modport == IntfModport.MASTER:
            modport = IntfModport.SLAVE
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


def create_intf(
        rdlc,
        parent_node : AddrmapNode,
        intf_type : str,
        addr_width : int,
        data_width : int,
        prefix : str,
        modport : IntfModport,
        capitalize : bool = False,
        orig_intf  : "Intf|None" = None,
        N : int=1,
        ):
    
    override_params = get_intf_t_param_str(intf_type, addr_width, data_width, prefix, modport)

    param = rdlc.eval(override_params)

    new_intf_root = rdlc.elaborate(
            top_def_name=intf_type,
                inst_name=intf_type,
                parameters={'INTF': param, 'N': N}
            )
    new_intf = new_intf_root.get_child_by_name(intf_type)

    assert(isinstance(new_intf, AddrmapNode))

    return Intf(
            intf_node=new_intf,
            parent_node=parent_node,
            rdlc=rdlc,
            sig_prefix=prefix,
            modport=list(IntfModport)[modport.value],
            capitalize=capitalize,
            N=N,
            orig_intf=orig_intf)

def get_intf_t_param_str(
        intf_type : str,
        addr_width : int,
        data_width : int,
        prefix : str,
        modport : IntfModport,
        ) -> str:

    param = f"intf_t'{{name: \"{intf_type}\", DATA_WIDTH: {data_width}, ADDR_WIDTH: {addr_width}, prefix: \"{prefix}\", modport:Modport::{modport.name.lower()} }}"

    return param

def get_intf_cap_param_str(
        intf_type : str,
        addr_width : int,
        data_width : int,
        prefix : str,
        modport : IntfModport,
        cap : bool,
        ) -> str:
    cap_str =  cap.__str__().lower()

    param = f"intf_cap'{{name: \"{intf_type}\", DATA_WIDTH: {data_width}, ADDR_WIDTH: {addr_width}, prefix: \"{prefix}\", modport:Modport::{modport.name.lower()}, cap:{cap_str} }}"

    return param
