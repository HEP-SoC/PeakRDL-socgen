from systemrdl import RDLWalker, RDLListener
from systemrdl.node import Node, MemNode, RootNode, AddressableNode, RegNode, FieldNode, AddrmapNode
from typing import List, Union
import jinja2
import os
import math
import copy
from enum import Enum

from systemrdl.core.parameter import Parameter
from systemrdl.rdltypes.user_struct import UserStruct

from .bus import Bus, Signal, SignalType, BusRDL, create_bus


def isSubsystem(node : Node ):
    if not isinstance(node, AddrmapNode):
        return False
    if node.get_property("subsystem") is not None:
        return True 
    return False 

def getOrigTypeName(node : Node) -> str:
    if node.orig_type_name is not None:
        return node.orig_type_name
    else:
        return node.inst_name

class SubsystemListener(RDLListener):
    def __init__(self):
        self.subsystem_nodes = []
        self.subsystems = []
        # Dont print anything here

    def enter_Addrmap(self, node):
        if isSubsystem(node):
            self.subsystem_nodes.append(node)      

class Subsystem:
    def __init__(self,
            node : AddrmapNode,
            bus_rdlc
            ):
        print(node, bus_rdlc)
        # self.bus = APB_Bus(32, 32)
        self.root = node 
        self.bus_rdlc = bus_rdlc
        # for p in node.inst.parameters:
        #     print("Paremeter is: ", p.name, type(p.get_value()))

        self.bus_prop_inst = self.root.get_property("bus_inst")
        # print("Bus: ", self.bus_rdl.name, self.bus_rdl.ADDR_WIDTH, self.bus_rdl.DATA_WIDTH)
        print(self.bus_prop_inst.members)

        self.bus = create_bus(self.bus_rdlc,
                    bus_name=self.bus_prop_inst.name,
                    value={'name': self.bus_prop_inst.name,
                        'ADDR_WIDTH' : self.bus_prop_inst.ADDR_WIDTH,
                        'DATA_WIDTH': self.bus_prop_inst.DATA_WIDTH})

        self.masters = self.getMasters()

        self.slaves = self.getSlaves()
        self.subsystems = self.getSubsystems()

    def getBus(self, node : AddrmapNode):
        b_prop = node.get_property("bus_inst")
        return create_bus(self.bus_rdlc,
                    bus_name=b_prop.name,
                    value={'name': b_prop.name,
                        'ADDR_WIDTH' : b_prop.ADDR_WIDTH,
                        'DATA_WIDTH': b_prop.DATA_WIDTH})

    def getOrigTypeName(self, node : Node) -> str:
        if node.orig_type_name is not None:
            return node.orig_type_name
        else:
            return node.inst_name

    def getName(self, node : AddrmapNode):
        return self.getOrigTypeName(node)       

    def isAdapterNeeded(self, first : Bus, second : Bus):
        if first.name == second.name:
            return False
        else:
            return True

    def getAdapterName(self, first : Bus, second : Bus):
        if first.name == "nmi_bus" and second.name == "apb_bus":
            return "nmi2apb"
        elif first.name == "nmi_bus"  and second.name == "nmi_tmr_bus":
            return "nmi2nmi_tmr"
        elif first.name == "apb_bus"  and second.name == "apb_tmr_bus":
            return "apb2apb_tmr"
        elif first.name == "apb_tmr_bus"  and second.name == "apb_bus":
            return "apb_tmr2apb"
        else:
            assert("Adapter not supported")

    def getSlaves(self):
        slaves = []
        for c in self.root.children():
            if self.isSlave(c):
                slaves.append(c)

        return slaves

    def getSubsystems(self):
        subsystems = []
        for c in self.root.children():
            if self.isSubsystem(c):
                s = Subsystem(c, self.bus_rdlc)
                subsystems.append(s)

        return subsystems

    def getMasters(self):
        masters = []
        for c in self.root.children():
            if self.isMaster(c):
                masters.append(c)

        return masters

    def getNumMasters(self):
        return len(self.getMasters())

    def getNumMasterPorts(self):
        num_masters = self.getNumMasters()
        if num_masters == 0:  # If not masters, input of subsystem is master
            return 1
        else:
            return num_masters

    def getParameters(self, node : Node):
        params = []
        for p in node.inst.parameters:
            if self.isHwParam(p):
                params.append(p)

        return params

    def isHwParam(self, param : Parameter):
        if isinstance(param.get_value(), int):
            return True
        else:
            return False

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
