from systemrdl.node import AddrmapNode, SignalNode, Node
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

        self.is_clk = self.isClk()
        self.is_rst = self.isRst()


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


class Bus:
    def __init__(self, bus_node : AddrmapNode):
        self.node = bus_node
        self.name = self.getOrigTypeName(self.node)
        self.addr_width = self.getParamValue(self.node, "ADDR_WIDTH")
        self.data_width = self.getParamValue(self.node, "DATA_WIDTH")
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
