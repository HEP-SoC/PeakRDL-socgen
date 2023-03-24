from systemrdl import RDLWalker, RDLListener
from systemrdl.node import Node, MemNode, RootNode, AddressableNode, RegNode, FieldNode, AddrmapNode
from typing import List, Union
import jinja2
import os
import math
import copy
from enum import Enum

from systemrdl.core.parameter import Parameter

from .bus import Bus, Signal, SignalType

class Subsystem:
    def __init__(self, node : AddrmapNode):
        # self.bus = APB_Bus(32, 32)
        self.root = node 

        self.bus = Bus(self.getBus())

    def getBus(self):
        for c in self.root.children():
            if self.isBus(c):
                return c

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
            if self.isSlave(c):
                slaves.append(c)

        return slaves

    def getMasters(self):
        masters = []
        for c in self.root.children():
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
            # typ = s.get_property("signal_type")
            sig = Signal(s) # TODO type is not correct here
            signals.append(sig)
            
        return signals

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
            if self.isEndpoint(c):
                endpoints.append(c)
        return endpoints

    def getNumEndpoints(self):

        return len(self.getEndpoints())

    def getBusSignals(self, node : AddrmapNode): # TODO create signal class
        return self.bus.getSignals()

    def isSubsystem(self, node : Node ):
        if not isinstance(node, AddrmapNode):
            return False
        if node.get_property("subsystem") is not None:
            return True 
        return False 

    def isBus(self, node : Node ):
        if not isinstance(node, AddrmapNode):
            return False
        if node.get_property("bus") is not None:
            return True 
        return False 

    def isMaster(self, node : Node):
        if not isinstance(node, AddrmapNode):
            return False
        if node.get_property("master") is not None:
            return True 
        return False 

    def isAddrmap(self, node : Node):
        if isinstance(node, AddrmapNode):
            return True 
        return False

    def isSlave(self, node : Node ):
        return self.isAddrmap(node) and not self.isMaster(node) and not self.isSubsystem(node) and not self.isBus(node)

    def isEndpoint(self, node : Node):
        return self.isAddrmap(node) and self.isSlave(node) or self.isSubsystem(node)
