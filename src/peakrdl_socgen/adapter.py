from typing import Tuple
from systemrdl import RDLCompiler
from systemrdl.node import AddrmapNode
from .module import Module
from .intf import Intf, IntfModport, Signal
from .intc import IntcBase

 
class Adapter(Module):
    def __init__(self, 
            adapt_from : Intf,
            adapt_to : Intf,
            rdlc : RDLCompiler,
            ):
        self.adapt_from = adapt_from
        self.adapt_to = adapt_to
        self.ext_ports = [adapt_from, adapt_to]

        self.rdlc = rdlc

        self.node = self.create_adapter_node()


        super().__init__(self.node, self.rdlc) # type: ignore


    def adapterDrivesExtPort(self):
        return self.ext_port.modport == IntfModport.MASTER

    def getLeftIntf(self):
        if self.adapt_from.modport == IntfModport.MASTER:
            return self.getSlaveIntfs()[0]

    def getRightIntf(self):
        if self.adapt_to.modport == IntfModport.MASTER:
            return self.getMasterIntfs()[0]


    @property
    def otherExtPort(self):
        if self.adapterDrivesExtPort():
            return self.getSlaveIntfs()[0]
        else:
            return self.getMasterIntfs()[0]

    def isDriver(self, s : Signal, intf : Intf):
        if intf not in [self.ext_port]:
            assert False, f"Interface is not connected to interconnect {intf.parent_node.inst_name}_{intf.sig_prefix}{intf.name}"

        if self.adapterDrivesExtPort():
            if s.isOnlyMiso():
                return True
            elif s.isOnlyMosi():
                return False
        else:
            if s.isOnlyMiso():
                return False
            elif s.isOnlyMosi():
                return True

        assert False, f"Interface is not connected to interconnect {intf.parent_node.inst_name}_{intf.sig_prefix}{intf.name}"


    def get_intfs(self):
        intfs = []
        for a in self.getAddrmaps():
            if a.get_property("intf"):
                intfs.append(self.construcIntf(a)) # type: ignore

        return intfs

    def construcIntf(self,
            intf : AddrmapNode,
            ):
        intf_inst = intf.get_property("intf_inst").members
        n_array = intf.get_property("n_array")
        try:
            cap = intf_inst['cap']
        except:
            cap = False

        return Intf(
                intf, 
                self.node, # type: ignore 
                self.rdlc,
                sig_prefix=intf_inst['prefix'],
                modport=list(IntfModport)[intf_inst['modport'].value],
                N=n_array,
                capitalize=cap,
                )

    def create_adapter_node(self):
        adapter_name = self.adapt_from.name.replace("_intf", "") + "2" + self.adapt_to.name.replace("_intf", "")
        inst_name = adapter_name + str(self.__hash__())[-3:]
        adapter = self.rdlc.elaborate(
                top_def_name=adapter_name,
                inst_name=inst_name,
                ).get_child_by_name(inst_name)

        return adapter
