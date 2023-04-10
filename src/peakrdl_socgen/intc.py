from systemrdl import RDLCompiler
from systemrdl.node import Node, MemNode, RootNode, AddressableNode, RegNode, FieldNode, AddrmapNode
from typing import List, Union, Dict, Any
import math
from enum import Enum

from systemrdl.core.parameter import Parameter
from systemrdl.rdltypes.array import ArrayPlaceholder
from systemrdl.rdltypes.user_struct import UserStruct, UserStructMeta
from systemrdl.rdltypes.user_enum import UserEnum


# from .bus import Bus, Signal, SignalType, BusRDL, create_bus, BusType
from .module import Module
from .intf import Intf, IntfModport, create_intf, Signal, get_intf_t_param_str

class InvalidAdapter(Exception):
    "Adapter cannot be created from given interfaces"
    pass

class IntcWrapper(Module):
    def __init__(self,
            rdlc : RDLCompiler,
            subsystem_node : "Subsystem", # type: ignore
            ext_slv_intfs : List[Intf],
            ext_master_ports : List[Intf],
            ):
        self.rdlc = rdlc
        self.isIntcWrap = True
        self.parent_node = subsystem_node.node
        self.subsystem_node = subsystem_node

        self.ext_slv_intfs = ext_slv_intfs
        self.ext_master_ports = ext_master_ports

        intc_node = self.create_intc_wrap_node()
        assert isinstance(intc_node, AddrmapNode)
        super().__init__(intc_node, self.rdlc)

        self.adapters = self.create_adapters(self.determineIntc())

        self.intc = self.create_intc()

    def getOrigTypeName(self) -> str:
        return self.node.inst_name

    def getSigVerilogName(self, s : Signal, intf : Intf | None = None) -> str:
        if intf is None:
            return s.name
        if intf.parent_node == self.node:
            return s.name
        else:
            return intf.parent_node.inst_name + "_" + s.name
    
    def create_intc(self):
        intc = self.determineIntc()

        # Find all interconnect master ports, Masters of adapters and slaves to interconnect wrap
        intc_slave_ports = []
        for ad in self.adapters:
            intf = ad.otherExtPort
            if intf.modport == IntfModport.MASTER and intf.name == intc.intf_type_name:
                intc_slave_ports.append(intf)
        for intf in self.intfs:
            if intf.modport == IntfModport.SLAVE and intf.name == intc.intf_type_name:
                intc_slave_ports.append(intf)

        # Find all interconnect slave ports, Slaves of self.adapters and masters to interconnect wrap
        intc_master_ports = []
        for ad in self.adapters:
            intf = ad.otherExtPort
            if intf.modport == IntfModport.SLAVE and intf.name == intc.intf_type_name:
                intc_master_ports.append(intf)
        for intf in self.intfs:
            if intf.modport == IntfModport.MASTER and intf.name == intc.intf_type_name:
                intc_master_ports.append(intf)
        
        return Intc(
                self.rdlc,
                intc_slave_ports,
                intc_master_ports,
                intc,
                subsystem_node=self.subsystem_node
                )

    def create_adapters(self, intc : "IntcBase") -> List["Adapter"]:
        adapters = []
        for intf in self.intfs:
            try:
                adapter = Adapter(intf, intc, self.rdlc)
            except InvalidAdapter:
                adapter = None
                pass
            if adapter is not None:
                adapters.append(adapter)
        return adapters
     
    def determineIntc(self) -> "IntcBase":
        slave_intfs = self.getSlaveIntfs()
        intf_type_cnt = {}
        for intf in slave_intfs:
            intf_type_cnt[intf.name] = 0
        for intf in slave_intfs:
            intf_type_cnt[intf.name] += 1

        max_intf = max(intf_type_cnt, key=intf_type_cnt.get) # type: ignore

        intc_type = max_intf.replace("_intf", "_interconnect")

        return IntcBase(intc_type, max_intf)

    def create_intc_wrap_node(self):
        
        params = r"'{"
        ports = [*self.ext_slv_intfs, *self.ext_master_ports]
        for i, intf in enumerate(ports):
            modport = None
            if intf in self.ext_slv_intfs:
                modport = IntfModport.SLAVE
            elif intf in self.ext_master_ports:
                modport = IntfModport.MASTER
            assert modport is not None

            if intf.parent_node == self.parent_node: # if interface is from top node dont add prefix of instantiation
                prefix = intf.sig_prefix
            else:
                prefix = intf.parent_node.inst_name + "_" + intf.sig_prefix

            params = params + get_intf_t_param_str(
                intf_type=intf.name,
                addr_width=intf.addr_width,
                data_width=intf.data_width,
                # prefix=intf.parent_node.inst_name + "_" + intf.sig_prefix,
                prefix=prefix,
                modport=modport
                )
            if i < len(ports)-1:
                params = params + ", "
        params = params + r"}"
        override_params = self.rdlc.eval(params)

        new_intc = self.rdlc.elaborate(
                top_def_name="interconnect_wrap",
                inst_name= self.parent_node.inst_name + "_intc_wrap",
                parameters= {'INTF': override_params},
                ).get_child_by_name(self.parent_node.inst_name + "_intc_wrap")

        return new_intc

class Adapter(Module):
    def __init__(self, 
            intf : Intf,
            intc : "IntcBase",
            rdlc : RDLCompiler,
            ):

        self.rdlc = rdlc
        self.ext_port = intf
        self.node = self.create_adapter(intf, intc)

        super().__init__(self.node, self.rdlc) # type: ignore

    
    def adapterDrivesExtPort(self):
        return self.ext_port.modport == IntfModport.MASTER

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

        return Intf(
                intf, 
                self.node, # type: ignore 
                self.rdlc,
                sig_prefix=intf_inst['prefix'],
                modport=list(IntfModport)[intf_inst['modport'].value],
                N=n_array
                )

    def create_adapter(self,
            intf : Intf,
            intc : "IntcBase",
            ):
        if intf.name != intc.intf_type_name:
            adapter_name = ""
            if intf.modport == IntfModport.MASTER:
                adapter_name = intc.intf_type_name.replace("_intf", "") + "2" + intf.name.replace("_intf", "")
            elif intf.modport == IntfModport.SLAVE:
                adapter_name = intf.name.replace("_intf", "") + "2" + intc.intf_type_name.replace("_intf", "")

            adapter = self.rdlc.elaborate(
                    top_def_name=adapter_name,
                    inst_name= adapter_name,
                    ).get_child_by_name(adapter_name)

            return adapter

        raise InvalidAdapter

class IntcBase:
    def __init__(self, 
            type_name : str,
            intf_type_name : str,
            ):
        self.intc_type_name = type_name
        self.intf_type_name = intf_type_name

class Intc(Module):
    def __init__(self,
            rdlc : RDLCompiler,
            ext_slv_intfs : List[Intf],
            ext_mst_intfs : List[Intf],
            intc_base  : IntcBase,
            subsystem_node : "Subsystem", # type: ignore
            ):
        self.rdlc = rdlc
        self.ext_slv_intfs = ext_slv_intfs
        self.ext_mst_intfs = ext_mst_intfs
        self.intc_base = intc_base
        self.subsystem_node = subsystem_node

        all_ports = [*self.ext_slv_intfs, *self.ext_mst_intfs]
        same_intf = all(x.name == all_ports[0].name for x in all_ports)
        assert same_intf, f"All interfaces to interconnect must be same type, {[ intf.name for intf in all_ports ]}"

        self.node = self.create_intc_node()

        super().__init__(self.node, self.rdlc)

    def get_intfs(self):
        return [self.getSlaveIntf(), self.getMasterIntf()]

    def isDriver(self, s : Signal, intf : Intf):
        if intf in self.ext_slv_intfs:
            if s.isOnlyMiso():
                return True
            elif s.isOnlyMosi():
                return False

        if intf in self.ext_mst_intfs:
            if s.isOnlyMiso():
                return False
            elif s.isOnlyMosi():
                return True

        assert False, f"Interface is not connected to interconnect {intf.parent_node.inst_name}_{intf.sig_prefix}{intf.name}"

    def create_intc_node(self) -> AddrmapNode:

        intc_params = self.getIntcParams()
        intc_name = self.intc_base.intc_type_name


        param_values = {
                'N_SLAVES'   : len(self.ext_mst_intfs),
                'DATA_WIDTH' : max(intc_params['data_w'], intc_params['data_w']),
                'ADDR_WIDTH' : max(intc_params['addr_w'], intc_params['addr_w']),
                }
        if len(self.ext_slv_intfs) > 1:
            param_values['N_MASTERS'] = len(self.ext_slv_intfs)

        mmap_params = self.get_intc_mmap_type(intc_name)
        if mmap_params is not None:
            param_values.update(mmap_params)

        root = self.rdlc.elaborate(
                top_def_name=intc_name,
                inst_name=intc_name + "_i",
                parameters = param_values,
                )
        new_intc = root.find_by_path(intc_name + "_i")


        return new_intc # type: ignore

    def get_intc_mmap_type(self, intc_name : str): 
        dflt_intc = self.rdlc.elaborate(
                top_def_name=intc_name,
                inst_name="default_" + intc_name,
                ).get_child_by_name("default_" + intc_name)
        assert dflt_intc is not None

        params = {}
        for p in dflt_intc.inst.parameters:
            # MEM_MAP scheme, array of START, END adresses
            if p.name == "MEM_MAP" and isinstance(p.param_type, ArrayPlaceholder):
                if p.param_type.element_type == int:
                    params['MEM_MAP'] = []
                    for c in self.subsystem_node.getSlaveNodes():
                        params['MEM_MAP'].extend([c.absolute_address, c.absolute_address + c.size])

            # SLAVE_ADDR, SLAVE_MASK scheme
            if p.name == "SLAVE_ADDR" and isinstance(p.param_type, ArrayPlaceholder):
                if p.param_type.element_type == int:
                    params['SLAVE_ADDR'] = []
                    for c in reversed(self.subsystem_node.getSlaveNodes()):
                        params['SLAVE_ADDR'].append(c.absolute_address)

            if p.name == "SLAVE_MASK" and isinstance(p.param_type, ArrayPlaceholder):
                if p.param_type.element_type == int:
                    params['SLAVE_MASK'] = []
                    for c in reversed(self.subsystem_node.getSlaveNodes()):
                        mask = self.fillOnesFromLeft(c.size, 32) # TODO width
                        params['SLAVE_MASK'].append(mask)

        return params

    def fillOnesFromLeft(self, num, width):
        ret = 0
        for i in reversed(range(0, width)):
            if num & (1<<i) == 0:
                ret = ret |  1<<i
            else:
                return ret | num

    def getIntcParams(self):
        max_dataw = max([*self.ext_slv_intfs, *self.ext_mst_intfs], key=lambda intf: intf.data_width).data_width
        max_addrw = max([*self.ext_slv_intfs, *self.ext_mst_intfs], key=lambda intf: intf.addr_width).addr_width

        return {'data_w': max_dataw, 'addr_w': max_addrw}

    def getSlaveIntf(self):
        slaves = []
        for c in self.getAddrmaps():
            if c.get_property("intf"):
                intf_inst = c.get_property("intf_inst")
                if intf_inst.modport.name == "slave":
                    N = c.get_property("n_array")
                    intf = Intf(c,
                                self.node,
                                self.rdlc,
                                sig_prefix=intf_inst.prefix,
                                modport=list(IntfModport)[intf_inst.modport.value],
                                N=N,
                                )
                    slaves.append(intf)
        assert len(slaves) == 1, "Only 1 slave port allowed in interconnect"

        return slaves[0]

    def getMasterIntf(self):
        masters = []
        for c in self.getAddrmaps():
            if c.get_property("intf"):
                intf_inst = c.get_property("intf_inst")
                if intf_inst.modport.name == "master":
                    N = c.get_property("n_array")
                    intf = Intf(c,
                                self.node,
                                self.rdlc,
                                sig_prefix=intf_inst.prefix,
                                modport=list(IntfModport)[intf_inst.modport.value],
                                N=N,
                                )
                    masters.append(intf)
        assert len(masters) == 1, "Only 1 slave port allowed in interconnect"

        return masters[0]
