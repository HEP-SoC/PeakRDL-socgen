from systemrdl import RDLWalker, RDLListener
from systemrdl.node import Node, MemNode, RootNode, AddressableNode, RegNode, FieldNode, AddrmapNode
from typing import List, Union
import jinja2
import os
import math
import copy
from enum import Enum

from systemrdl.core.parameter import Parameter

class SignalType(Enum):  # TODO make it same type as the RDL one
    OUTPUT = 0
    INPUT  = 1
    BIDIRECTIONAL = 2
    TRISTATE = 3
    CLK = 4
    RST = 5
    WIRE = 6
    BLANK = 7

# class SignalPolarity(Enum):
#     ACTIVE_LOW   = 0
#     ACTIVE_HIGH  = 1
#     RISING_EDGE  = 2
#     FALLING_EDGE = 3
#     BUS = 4

class Signal:
    def __init__(self,
            name : str,
            width : int,
            signal_type : SignalType=SignalType.WIRE,
            ):

        self.name = name
        self.width = width

        self.signal_type = signal_type

class Bus:
    def __init__(self, name : str, addr_width : int, data_width : int):
        self.name = name
        self.addr_width = addr_width
        self.data_width = data_width
        self.interconnect_name = name + "_interconnect"

        self.signals = []

    def add_signal(self, name : str, width : int=1):
        sig = Signal(name, width)
        self.signals.append(sig)

    def getSignals(self):
        return self.signals

class NMI_Bus(Bus):
    def __init__(self, addr_width : int=32, data_width : int=32):
        Bus.__init__(self, "nmi", addr_width, data_width) 

        self.add_signal("mem_valid")
        self.add_signal("mem_ready")
        self.add_signal("mem_instr")
        self.add_signal("mem_addr", addr_width)
        self.add_signal("mem_wdata", data_width)
        self.add_signal("mem_rdata", data_width)
        self.add_signal("mem_wstrb", math.ceil(data_width/8))

# class RTL_Param(Parameter):
#     def __init__(self):
#         Parameter()

class Subsystem:
    def __init__(self, node : AddrmapNode):
        self.bus = NMI_Bus(32, 32)
        self.root = node 

    def getOrigTypeName(self, node : Node) -> str:
        if node.orig_type_name is not None:
            return node.orig_type_name
        else:
            return node.inst_name

    def getName(self, node : AddrmapNode):
        return self.getOrigTypeName(node)       

    def getSlaves(self):
        slaves = []
        for c in self.root.children():
            if isinstance(c, AddrmapNode):
                if self.isSlave(c):
                    slaves.append(c)

        return slaves

    def getMasters(self):
        masters = []
        for c in self.root.children():
            if isinstance(c, AddrmapNode):
                if self.isMaster(c):
                    masters.append(c)

        return masters

    def getNumMasters(self):
        return len(self.getMasters())

    def getParameters(self, node : Node):
        params = []
        for p in node.inst.parameters:
            params.append(p)

        return params

    def getSignals(self, node : AddrmapNode):
        signals = []
        for s in node.signals():
            typ = s.get_property("signal_type")
            sig = Signal(s.inst_name, s.width, typ.name) # TODO type is not correct here
            signals.append(sig)
            
        return signals

    def isClk(self, signal : Signal):
        if signal.signal_type == 'clk':
            return True

    def isRst(self, signal : Signal):
        if signal.signal_type == 'rst':
            return True

    def getMemmapParam(self):
        str = ""
        addrw = self.bus.addr_width
        hexf = math.ceil(self.bus.addr_width//4)
        for c in self.getEndpoints():
            if str != "":
                str = str + ","
            str = str + f" {addrw}'h{c.absolute_address:0{hexf}x}, {addrw}'h{c.absolute_address+c.size:0{hexf}x}"

        return str 


    def getEndpoints(self):
        endpoints = []
        for c in self.root.children():
            if isinstance(c, AddrmapNode) and not self.isMaster(c):
                endpoints.append(c)
        return endpoints

    def getNumEndpoints(self):

        return len(self.getEndpoints())

    def getBusSignals(self, node : AddrmapNode): # TODO create signal class
        return self.bus.getSignals()

    def isSubsystem(self, node : AddrmapNode ):
        if node.get_property("subsystem") is not None:
            return True 
        return False 

    def isMaster(self, node : AddrmapNode):
        if node.get_property("master") is not None:
            return True 
        return False 

    def isSlave(self, node : AddrmapNode ):

        return not self.isMaster(node) and not self.isSubsystem(node)
