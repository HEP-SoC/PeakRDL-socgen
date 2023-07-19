from sys import intern
from colorama import init
from systemrdl import RDLCompiler, RDLListener
from systemrdl.node import Node, AddrmapNode
from typing import List

from peakrdl_socgen.intc_wrapper import IntcWrapper
from .module import Module
from .intf import Intf, IntfPort, Modport
from .intc import Intc
from .signal import Signal
from .adapter import AdaptersPath


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
        self.signals = self.propagateSignals()
        self.connections = [] #self.getConnections()
    
        self.initiators = self.getInitiators()
        self.endpoints = self.getEndpoints()

        # self.intc_wraps = self.getUserDefinedIntcws()
        self.intc_wraps = []

        self.intcs = []
        self.adapter_paths = []

        self.intcs.extend(self.getUserDefinedIntcs())
        self.intcs.append(self.create_intc(self.initiators, self.endpoints))

    def getAllModules(self) -> "List[Modules]":
        mods = self.getModules()
        mods.extend(self.intcs)
        for ap in self.adapter_paths:
            mods.extend(ap.adapters)
        return mods

    def getAllAdapters(self):
        adapters = []
        for ap in self.adapter_paths:
            adapters.extend(ap.adapters)
        return adapters


    def propagateSignals(self) -> "List[Signal]":
        signals = []
        for mod in self.modules:
            for s in mod.signals:
                if s.node.get_property("propagate", default=False):
                    signals.append(Signal(
                        node=s.node, 
                        prefix=mod.node.inst_name + "_" + s.prefix,
                        cap=s.cap
                        ))
        return self.signals + signals 

    # def getConnection(self, first : Intf, second : Intf):
    #     if first.module_node == self.node and second.module_node == self.node:
    #         assert first.modport != second.modport, f"If both intfs are subsystem port, they need to be different modport"
    #         if first.modport == Modport.slave:
    #             return (first, second)
    #         else:
    #             return (second, first)
    #
    #     if first.module_node == self.node or second.module_node == self.node: # But not both
    #         assert first.modport == second.modport, f"If one intf is subsystem port, and the other is module port, they need to be the same modport"
    #         if first.modport == Modport.slave:
    #             return (first, second)
    #         else:
    #             return (second, first)
    #
    #     if first.module_node != self.node and second.module_node != self.node:
    #         assert first.modport != second.modport, f"Intf modports must be different to connect them"
    #         if first.modport == Modport.master:
    #             return (first, second)
    #         else:
    #             return (second, first)
    #
    #     assert False, "Error reached end of this function"
    #
    # def getConnections(self):
    #     conn_p = self.node.get_property("connections", default = [])
    #
    #     conns = []
    #     for conn in conn_p:
    #         assert len(conn.split("->")) == 2, f"Wrong format for connection {conn}"
    #         conn = conn.split("->")
    #         conns.append((conn[0].replace(" ", ""), conn[1].replace(" ", "")))
    #
    #     connections = []
    #     for first, second in conns:
    #     # for first, second in zip(conn_p.split())
    #         conn_ifs = (None, None)
    #         for i in self.getChildIntfs():
    #             node_rel = i.module_node.get_path().replace(self.node.get_path(), "")
    #             node_rel = node_rel[1:] if node_rel.startswith('.') else node_rel
    #
    #             if node_rel + "." + i.sig_prefix == first:
    #                 conn_ifs = (i, conn_ifs[1])
    #             if node_rel + "." + i.sig_prefix == second:
    #                 conn_ifs = (conn_ifs[0], i)
    #
    #         assert all(x is not None for x in conn_ifs), f"Could not find one of the connections: {first} = {conn_ifs[0]} | {second} = {conn_ifs[1]}"
    #         assert conn_ifs[0].modport != conn_ifs[1].modport, f"Connection interfaces need to be slave and master {conn_ifs[0].sig_prefix}, {conn_ifs[1].sig_prefix}" # type: ignore  #  TODO slave to slave allowed if one of the intfs is port of subsystem ??? NOT needed checked in intc_wrapper createConnectionIntfs????
    #         connections.append(conn_ifs)
    #
    #     return connections
    #

    def getUserDefinedIntcs(self):
        intcs = []
        intc_l = self.node.get_property('intc_l', default=[])

        for intc in intc_l:
            ext_mst_ports = []
            ext_slv_ports = []

            for mst in intc.mst_ports:
                intf = self.findPortInChildren(mst)
                if intf in self.endpoints:
                    self.endpoints.remove(intf)
                ext_mst_ports.append(intf)

            for slv in intc.slv_ports:
                intf = self.findPortInChildren(slv)
                if intf in self.initiators:
                    self.initiators.remove(intf)
                ext_slv_ports.append(intf)

            intcs.append(
                    self.create_intc(
                        slv_ports=ext_slv_ports,
                        mst_ports=ext_mst_ports,
                        inst_prefix=intc.name + "_",
                        )
                    )
        return intcs


    def findPortInChildren(self, string : str):
        for intf in self.getChildPorts():
            node_rel = intf.module.node.get_path().replace(self.node.get_path(), "")
            node_rel = node_rel[1:] if node_rel.startswith('.') else node_rel
            if (node_rel + "." + intf.prefix) == string:
                return intf
        assert False, f"Could not find interface {string}"

    def getModules(self):
        modules = []
        for node in self.getAddrmaps():
            if node.get_property('subsystem'):
                modules.append(Subsystem(node, self.rdlc))
            else:
                modules.append(Module(node, self.rdlc))

        return modules

    # def getName(self):
    #     return self.getOrigTypeName()       

    def getEndpoints(self) -> List[Intf]:
        endpoints = [intf for module in self.modules for intf in module.getSlavePorts()]
        endpoints.extend(self.getMasterPorts())
        return endpoints

    def getInitiators(self) -> List[Intf]:
        initiators = [intf for module in self.modules for intf in module.getMasterPorts()]
        initiators.extend(self.getSlavePorts())
        return initiators

    def getPorts(self) -> List[Intf]:
        return self.getEndpoints() + self.getInitiators()

    def getChildPorts(self):
        return [port for module in self.modules for port in module.ports]

    # def dotGraphGetModules(self):
    #     modules = [mod for mod in self.modules if not isinstance(mod, IntcWrapper) and not isinstance(mod, Subsystem)]
    #     # wrap_modules = [mod for mod in self.intc_wrap.adapters ] + [self.intc_wrap.intc]
    #     return modules #+ wrap_modules


    ### INTERCONNECT

    def determineIntc(self,
                      initiators : "List[IntfPort]") -> "tuple[str, str]":
        intf_type_cnt = {}
        for intf in initiators:
            intf_type_cnt[intf.type] = 0
        for intf in initiators:
            intf_type_cnt[intf.type] += 1

        max_intf = max(intf_type_cnt, key=intf_type_cnt.get) # type: ignore

        intc_type = max_intf.replace("_intf", "_interconnect")

        return intc_type, max_intf

    def create_intc(self,
                    slv_ports : "List[Intf]",
                    mst_ports : "List[Intf]",
                    inst_prefix : str="",
                    ):

        _, intf_type = self.determineIntc(slv_ports)
        ports_need_adapter = [port for port in slv_ports + mst_ports if port.type != intf_type]

        for p in ports_need_adapter:
            self.adapter_paths.append(AdaptersPath(
                    adapt_from=slv_ports[0],
                    adapt_to=p,
                    rdlc=self.rdlc,
                    )
                  )

            for cnt, mst_p in enumerate(mst_ports):
                if mst_p == p:
                    mst_ports[cnt] = self.adapter_paths[-1].adapters[0].slv_port;


        for p in slv_ports:
            if p.modport.name == "slave":
                assert p.module.node == self.node, f"Interface port {p} is slave but is not a port of the subsystem node"

        for p in mst_ports:
            if p.modport.name == "master":
                assert p.module.node == self.node, f"Interface port {p} is master but is not a port of the subsystem node"

        # assert all(intf.type == slv_ports[0].type for intf in slv_ports + mst_ports), "Not all ports of the interconnect are of the same protocol"
        # intc_name = slv_ports[0].type.replace("_intf_node", "_interconnect")

        return Intc(
                rdlc=self.rdlc,
                ext_slv_ports=slv_ports,
                ext_mst_ports=mst_ports,
                subsystem_node=self.node,
                inst_prefix=inst_prefix,
                )
