from sys import intern
from systemrdl import RDLCompiler, RDLListener
from systemrdl.node import Node, AddrmapNode
from typing import List

from peakrdl_socgen.intc_wrapper import IntcWrapper
from .module import Module
from .intf import Intf, IntfModport
from .signal import Signal


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
        self.signals = self.inheritSignals()
        self.connections = self.getConnections()

        self.startpoints = self.getStartpoints()
        self.endpoints = self.getEndpoints()

        self.intc_wraps = self.getUserDefinedIntcws()

        if len(self.startpoints ) > 0 and len(self.endpoints) > 0:
            self.intc_wraps.append(IntcWrapper(
                    rdlc=rdlc,
                    subsystem_node=self,
                    ext_slv_intfs=self.startpoints,
                    ext_mst_intfs=self.endpoints,
                    ext_connections=self.connections,
                    ))

        self.modules.extend(self.intc_wraps)

    def inheritSignals(self):
        signals = []
        for mod in self.modules:
            for s in mod.signals:
                if not (s.is_rst or s.is_clk):
                    signals.append(Signal(
                        node=s.node, 
                        prefix=mod.node.inst_name + "_" + s.prefix,
                        capitalize=s.capitalize
                        ))
        return self.signals + signals 

    def getConnection(self, first : Intf, second : Intf):
        if first.parent_node == self.node and second.parent_node == self.node:
            assert first.modport != second.modport, f"If both intfs are subsystem port, they need to be different modport"
            if first.modport == IntfModport.SLAVE:
                return (first, second)
            else:
                return (second, first)

        if first.parent_node == self.node or second.parent_node == self.node: # But not both
            assert first.modport == second.modport, f"If one intf is subsystem port, and the other is module port, they need to be the same modport"
            if first.modport == IntfModport.SLAVE:
                return (first, second)
            else:
                return (second, first)

        if first.parent_node != self.node and second.parent_node != self.node:
            assert first.modport != second.modport, f"Intf modports must be different to connect them"
            if first.modport == IntfModport.MASTER:
                return (first, second)
            else:
                return (second, first)

        assert False, "Error reached end of this function"

    def getConnections(self):
        conn_p = self.node.get_property("connections", default = [])

        conns = []
        for conn in conn_p:
            assert len(conn.split("->")) == 2, f"Wrong format for connection {conn}"
            conn = conn.split("->")
            conns.append((conn[0].replace(" ", ""), conn[1].replace(" ", "")))

        connections = []
        for first, second in conns:
        # for first, second in zip(conn_p.split())
            conn_ifs = (None, None)
            for i in self.getChildIntfs():
                node_rel = i.parent_node.get_path().replace(self.node.get_path(), "")
                node_rel = node_rel[1:] if node_rel.startswith('.') else node_rel

                if node_rel + "." + i.sig_prefix == first:
                    conn_ifs = (i, conn_ifs[1])
                if node_rel + "." + i.sig_prefix == second:
                    conn_ifs = (conn_ifs[0], i)

            assert all(x is not None for x in conn_ifs), f"Could not find one of the connections: {first} = {conn_ifs[0]} | {second} = {conn_ifs[1]}"
            assert conn_ifs[0].modport != conn_ifs[1].modport, f"Connection interfaces need to be slave and master {conn_ifs[0].sig_prefix}, {conn_ifs[1].sig_prefix}" # type: ignore  #  TODO slave to slave allowed if one of the intfs is port of subsystem ??? NOT needed checked in intc_wrapper createConnectionIntfs????
            connections.append(conn_ifs)

        return connections

    def getUserDefinedIntcws(self):
        intcws = []
        intcw_l = self.node.get_property('intcw_l', default=[])

        intcw_dict = {}
        for intcw in intcw_l:
            ext_mst_ports = []
            ext_slv_ports = []

            for mst in intcw.mst_ports:
                intf = self.getIntfFromString(mst)
                if intf in self.endpoints:
                    self.endpoints.remove(intf)
                ext_mst_ports.append(intf)

            for slv in intcw.slv_ports:
                intf = self.getIntfFromString(slv)
                if intf in self.startpoints:
                    self.startpoints.remove(intf)
                ext_slv_ports.append(intf)

            intcws.append(
                    IntcWrapper(
                        rdlc=self.rdlc,
                        subsystem_node=self,
                        ext_slv_intfs=ext_slv_ports,
                        ext_mst_intfs=ext_mst_ports,
                        ext_connections=[],
                        name=intcw.name,
                        )
                    )

            intcw_dict[intcw.name] = {'ext_slv_ports' : ext_slv_ports, 'ext_mst_ports' : ext_mst_ports}

        return intcws


    def getIntfFromString(self, string : str):
        for intf in self.getChildIntfs():
            node_rel = intf.parent_node.get_path().replace(self.node.get_path(), "")
            node_rel = node_rel[1:] if node_rel.startswith('.') else node_rel
            if (node_rel + "." + intf.sig_prefix) == string:
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

    def getChildIntfs(self):
        return [intf for module in self.modules for intf in module.intfs]

    def dotGraphGetModules(self):
        modules = [mod for mod in self.modules if not isinstance(mod, IntcWrapper) and not isinstance(mod, Subsystem)]
        # wrap_modules = [mod for mod in self.intc_wrap.adapters ] + [self.intc_wrap.intc]
        return modules #+ wrap_modules

