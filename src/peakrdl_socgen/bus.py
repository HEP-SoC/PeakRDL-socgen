from typing import Dict, Any
from systemrdl.node import AddrmapNode, SignalNode, Node, RootNode
from systemrdl.core.parameter import Parameter
from enum import Enum

class SignalType(Enum):  # TODO make it same type as the RDL one
    OUTPUT = 0
    INPUT  = 1
    BIDIRECTIONAL = 2
    TRISTATE = 3
    CLK = 4
    RST = 5
    WIRE = 6
    BLANK = 7

class Signal:
    def __init__(self,
            node : SignalNode
            ):

        self.node = node
        self.name = node.inst_name # TOOD check if correct
        self.width = node.width
        self.ss =  node.get_property('ss', default=False)    != False
        self.miso = node.get_property('miso', default=False) != False
        self.mosi = node.get_property('mosi', default=False) != False
        self.bidir = self.miso and self.mosi
        self.is_clk = self.isClk()
        self.is_rst = self.isRst()


    def isShared(self):
        return not self.ss and not self.miso  # TODO what happens for bidir?

    def isOnlyMiso(self):
        return self.miso and not self.mosi

    def isOnlyMosi(self):
        return self.mosi and not self.miso

    def isClk(self):
        typ = self.node.get_property("signal_type", default=False)
        if typ == False:
            return False
        if typ.name == 'clk':
            return True
        return False

    def isRst(self):
        typ = self.node.get_property("signal_type", default=False)
        if typ == False:
            return False
        if typ.name == 'rst':
            return True
        return False

    def print(self):
        print("Signal: ", self.name, " Width: ", self.width, " SS: ", self.ss, " MOSI: ", self.mosi, " MISO ", self.miso)

class BusRDL:
    def __init__(self,
            name : str,
            addr_width : int,
            data_width : int,
            ):
        self.name = name
        self.addr_width = addr_width
        self.data_width = data_width

class Bus:
    def __init__(self, bus_node : AddrmapNode):
        self.node = bus_node

        prop = self.node.get_property("bus_inst")
        self.name = prop.name
        self.addr_width = prop.ADDR_WIDTH
        self.data_width = prop.DATA_WIDTH
        self.interconnect_name = self.node.get_property("interconnect_name")

        self.signals = self.getSignals(self.node)

    def getSignals(self, bus_node : AddrmapNode):
        signals = []
        if self.isBus(bus_node):
            for s in bus_node.signals():
                signals.append(Signal(s))
            return signals
        return None

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

    def isBus(self, node : Node ): # TODO move to common
        if not isinstance(node, AddrmapNode):
            return False
        if node.get_property("bus") is not None:
            return True 
        return False 

    def isAdapterNeeded(self, first : "Bus", second : "Bus"):
        if first.name == second.name:
            return False
        else:
            return True

    def print(self):
        print("Bus: ", self.name,
                " Addr width: ", self.addr_width,
                " Data width: ", self.data_width,
                " Interconnect name ", self.interconnect_name)
        assert(self.signals is not None)
        for s in self.signals:
            s.print()

def create_bus(
        rdlc,
        bus_name : str,
        value : Dict[str, Any],
        bus_param_name : str = 'BUS',
        ):

    default_bus = rdlc.elaborate(
            top_def_name=bus_name,
            inst_name="new_inst",
            )
    assert(isinstance(default_bus, RootNode))
    bus_default = default_bus.get_child_by_name("new_inst")
    assert(isinstance(bus_default, AddrmapNode))

    override_param = get_param_override(bus_param_name, value, bus_default)

    new_bus_root = rdlc.elaborate(
            top_def_name=bus_name,
            inst_name=bus_name,
            parameters={bus_param_name: override_param}
            )
    new_bus = new_bus_root.get_child_by_name(bus_name)

    assert(isinstance(new_bus, AddrmapNode))

    return Bus(new_bus)

def get_param_override(name : str, value : Dict[str, Any], node : Node):
    for p in node.inst.parameters:
        if p.name == name:
            return p.param_type(value)
