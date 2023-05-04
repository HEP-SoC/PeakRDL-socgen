from jinja2 import ext
from systemrdl import RDLCompiler
from systemrdl.node import  AddrmapNode
from typing import List, Tuple

# from .bus import Bus, Signal, SignalType, BusRDL, create_bus, BusType
from .module import Module
from .intc import Intc
from .adapter import Adapter
from .intf import Intf, IntfModport, create_intf, get_intf_cap_param_str
from .signal import Signal

class InvalidAdapter(Exception):
    "Adapter cannot be created from given interfaces"
    pass

class IntcWrapper(Module):
    def __init__(self,
            rdlc : RDLCompiler,
            subsystem_node : "Subsystem", # type: ignore
            ext_slv_intfs : List[Intf],
            ext_mst_intfs : List[Intf],
            ext_connections : List[Tuple[Intf, Intf]],
            name : str|None = None
            ):
        self.rdlc = rdlc
        self.isIntcWrap = True
        self.parent_node = subsystem_node.node
        self.subsystem_node = subsystem_node
        self.name = name

        self.ext_slv_intfs = ext_slv_intfs
        self.ext_mst_intfs = ext_mst_intfs
        intc_node = self.create_intc_wrap_node()
        assert isinstance(intc_node, AddrmapNode)
        super().__init__(intc_node, self.rdlc)

        self.connections = self.createConnectionIntfs(ext_connections)
        self.assignOriginalIntfs()

        self.adapters = []
        self.intc = self.create_intc()


    @property
    def intfsNeedAdapter(self):
        _, intf_type = self.determineIntc()
        return [intf for intf in self.intfs if intf.name != intf_type]

    @property
    def intfsNoAdapter(self):
        _, intf_type = self.determineIntc()
        return [intf for intf in self.intfs if intf.name == intf_type]

    def groupSignals(self, first : Intf, second : Intf):
        conns = []
        for s in first.signals:
            other = second.findSignal(s.basename)
            assert other is not None, f"Could not find signal {s.name} in {second.name}"
            if s.miso:
                conns.append((s, other))
            else:
                conns.append((other, s))
        return conns

    def checkIfInConnections(self, intf : Intf):
        for conn in self.connections:
            if intf in conn:
                return True
        return False

    def create_intc(self):
        _, intf_type = self.determineIntc()

        intc_slave_ports = [intf for intf in self.intfsNoAdapter if intf.modport == IntfModport.SLAVE]
        intc_slave_ports = [slv for slv in intc_slave_ports if not self.checkIfInConnections(slv)]
        intc_master_ports = [intf for intf in self.intfsNoAdapter if intf.modport == IntfModport.MASTER]
        intc_master_ports = [mst for mst in intc_master_ports if not self.checkIfInConnections(mst)]

        data_width, addr_width = self.getIntcWidths()

        for intf in self.intfsNeedAdapter:      # TODO Connections that need adapters?
            intc_intf = create_intf(
                    rdlc=self.rdlc,
                    parent_node=self.node,
                    orig_intf=intf.orig_intf,
                    intf_type=intf_type,
                    addr_width=addr_width, # TODO
                    data_width=data_width, 
                    prefix=intf_type.replace("_intf", "") + "2" +  intf.name.replace("_intf", "") + "_" + intf.sig_prefix + "_", 
                    modport=intf.modport,
                    )
            if intc_intf.modport == IntfModport.SLAVE:
                intc_slave_ports.append(intc_intf)
            elif intc_intf.modport == IntfModport.MASTER:
                intc_master_ports.append(intc_intf)

            adapters = self.createAdaptersOnPath(intf, intc_intf)
            if adapters is not None:
                self.adapters.extend(adapters)

        return Intc(
                rdlc=self.rdlc,
                ext_slv_intfs=intc_slave_ports,
                ext_mst_intfs=intc_master_ports,
                subsystem_node=self.subsystem_node
                )

    def getAdaptersGlueIntfs(self):
        intfs = []
        for adapter in self.adapters:
            for intf in adapter.ext_ports:
                if not self.hasIntf(intf):
                    intfs.append(intf)
        return list(set(intfs)) # remove duplicates

    def createAdaptersOnPath(self, intf : Intf, intc_intf : Intf):
        available_adapters = ["axi2axi_lite", "axi_lite2apb", "nmi2apb", "pulpif2axi_lite", "pulpif2axi"] # TODO find it automatically
        adapter_paths = []

        if intf.name == intc_intf.name:
            return None

        adapter_name = None
        if intf.modport == IntfModport.MASTER:
            adapter_name =  intc_intf.name.replace("_intf", "") + "2" + intf.name.replace("_intf", "")
        elif intf.modport == IntfModport.SLAVE:
            adapter_name = intf.name.replace("_intf", "") + "2" + intc_intf.name.replace("_intf", "")

        if adapter_name in available_adapters:
            return [Adapter(adapt_from=intc_intf, adapt_to=intf, rdlc=self.rdlc)]

        fitting_slaves = []
        fitting_masters = []
        for a in available_adapters:
            if a.split("2")[0] == adapter_name.split("2")[0]: # type: ignore
                fitting_slaves.append(a)

            if a.split("2")[1] == adapter_name.split("2")[1]: # type: ignore
                fitting_masters.append(a)

        adapter_paths = []
        for slv in fitting_slaves:
            for mst in fitting_masters:
                if slv.split("2")[1] == mst.split("2")[0]:
                    adapter_paths.append([slv, mst])

        for cnt, adapter in enumerate(adapter_paths[0]): # IF MASTER TODO SLAVE
            if cnt == 0:
                adapt_to = create_intf(
                        rdlc=self.rdlc,
                        parent_node=self.node,
                        intf_type=adapter.split("2")[1] + "_intf",
                        addr_width=intf.addr_width,
                        data_width=intf.data_width,
                        prefix="TODO_I_DONT_KNOW_",
                        modport=intf.modport
                        )
                self.adapters.append(Adapter(adapt_from=intc_intf, adapt_to=adapt_to, rdlc=self.rdlc))
            elif cnt == len(adapter_paths[0]) - 1:
                adapt_from = create_intf(
                        rdlc=self.rdlc,
                        parent_node=self.node,
                        intf_type=adapter.split("2")[1] + "_intf",
                        addr_width=intf.addr_width,
                        data_width=intf.data_width,
                        prefix="LAST_ONE_TODO_",
                        modport=intf.modport
                        )
                self.adapters.append(Adapter(adapt_from=self.adapters[-1].adapt_to, adapt_to=intf, rdlc=self.rdlc))


        assert len(adapter_paths) > 0, f"Could not find appropriate adapter or combination for {intf.name} modport: {intf.modport} and {intc_intf.name}"


    def getIntcWidths(self) -> tuple[int, int]:
        max_dataw = max([*self.ext_slv_intfs, *self.ext_mst_intfs], key=lambda intf: intf.data_width).data_width
        max_addrw = max([*self.ext_slv_intfs, *self.ext_mst_intfs], key=lambda intf: intf.addr_width).addr_width
        return max_dataw, max_addrw

    def determineIntc(self) -> tuple[str, str]:
        slave_intfs = self.getSlaveIntfs()
        intf_type_cnt = {}
        for intf in slave_intfs:
            intf_type_cnt[intf.name] = 0
        for intf in slave_intfs:
            intf_type_cnt[intf.name] += 1

        max_intf = max(intf_type_cnt, key=intf_type_cnt.get) # type: ignore

        intc_type = max_intf.replace("_intf", "_interconnect")

        return intc_type, max_intf

    def create_intc_wrap_node(self):
        params = r"'{"
        ports = [*self.ext_slv_intfs, *self.ext_mst_intfs]
        for i, intf in enumerate(ports):
            modport = None
            if intf in self.ext_slv_intfs:
                modport = IntfModport.SLAVE
            elif intf in self.ext_mst_intfs:
                modport = IntfModport.MASTER
            assert modport is not None

            if intf.parent_node == self.parent_node: # if interface is from top node dont add prefix of instantiation
                prefix = intf.sig_prefix
            else:
                prefix = intf.parent_node.inst_name + "_" + intf.sig_prefix

            params = params + get_intf_cap_param_str(
                intf_type=intf.name,
                addr_width=intf.addr_width,
                data_width=intf.data_width,
                # prefix=intf.parent_node.inst_name + "_" + intf.sig_prefix,
                prefix=prefix,
                modport=modport,
                cap=intf.capitalize,
                )
            if i < len(ports)-1:
                params = params + ", "
        params = params + r"}"
        override_params = self.rdlc.eval(params)

        if self.name is None:
            name = self.parent_node.inst_name + "_intc_wrap"
        else:
            name = self.name + "_intc_wrap"

        new_intc = self.rdlc.elaborate(
                top_def_name="interconnect_wrap",
                inst_name=name,
                parameters= {'INTF': override_params},
                ).get_child_by_name(name)

        return new_intc

    def createConnectionIntfs(self, ext_connections):
        assert self.node is not None, "Intc wrapper node not created yet"
        connections = []
        for first, second in ext_connections:
            conn_ifs = (None, None)
            for intf in self.intfs:
                first_new_prefix = first.parent_node.inst_name + "_" + first.sig_prefix
                second_new_prefix = second.parent_node.inst_name + "_" + second.sig_prefix
                if first_new_prefix == intf.sig_prefix:
                    conn_ifs = (intf, conn_ifs[1])
                if second_new_prefix == intf.sig_prefix:
                    conn_ifs = (conn_ifs[0], intf)

            assert all(x is not None for x in conn_ifs), f"Could not find one of the connections: {first} = {conn_ifs[0]} | {second} = {conn_ifs[1]}"
            assert conn_ifs[0].modport != conn_ifs[1].modport, f"Connection interfaces need to be slave and master {conn_ifs[0].sig_prefix}, {conn_ifs[1].sig_prefix}" # type: ignore
            connections.append(conn_ifs)
        return connections

    def assignOriginalIntfs(self):
        for intf in self.intfs:
            for orig in [*self.ext_mst_intfs, *self.ext_slv_intfs]:
                if orig.parent_node.inst_name + "_" + orig.sig_prefix == intf.sig_prefix:
                    intf.orig_intf = orig

    def getOrigTypeName(self) -> str:
        return self.node.inst_name

    def getSigVerilogName(self, s : Signal, intf : Intf | None = None) -> str:
        if intf is None:
            return s.name
        if intf.parent_node == self.node:
            return s.name
        else:
            return intf.parent_node.inst_name + "_" + s.name
    

