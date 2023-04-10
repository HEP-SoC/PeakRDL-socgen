from systemrdl import RDLCompiler, RDLWalker, RDLListener, node
from systemrdl.node import Node, MemNode, RootNode, AddressableNode, RegNode, FieldNode, AddrmapNode
from typing import List, Union
import jinja2
import os
import math
import copy
from enum import Enum

from systemrdl.core.parameter import Parameter
from systemrdl.rdltypes.user_struct import UserStruct
from systemrdl.rdltypes.user_enum import UserEnum

from peakrdl_socgen import module
from peakrdl_socgen.intc import Intc, IntcWrapper
from peakrdl_socgen.intf import create_intf

from .module import Module
from .intf import Intf, IntfModport, Signal


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

class Subsystem(Module): # TODO is module and subsystem the same?
    def __init__(self,
            node : AddrmapNode,
            rdlc : RDLCompiler,
            ):
        super().__init__(node, rdlc)

        self.modules =  self.getModules() 


        self.intc_wrap = IntcWrapper(rdlc, self, self.getStartpoints(), self.getEndpoints())

        self.modules.append(self.intc_wrap)

    
    def getModules(self):
        # modules = []
        # for node in self.getAddrmaps():
        #     if node.get_property('subsystem'):
        #         print(node.get_path())
        #         modules.append(Subsystem(node, self.rdlc))
        #     else:
        #         modules.append(Module(node, self.rdlc))
        #
        # return modules
        return [Module(node, self.rdlc) for node in self.getAddrmaps()]

    def getName(self):
        return self.getOrigTypeName()       

    def getEndpoints(self) -> List[Intf]:
        endpoints = [intf for module in self.modules for intf in module.getSlaveIntfs()]
        endpoints.extend(self.getMasterIntfs())

        return endpoints

    def getStartpoints(self) -> List[Intf]:
        startpoints = [intf for module in self.modules for intf in module.getMasterIntfs()]
        startpoints.extend(self.getSlaveIntfs())

        return startpoints


