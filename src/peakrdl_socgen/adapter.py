from typing import Tuple, List
from systemrdl import RDLCompiler
from systemrdl.node import AddrmapNode
from systemrdl.rdltypes import UserStruct
from .module import Module
from .intf import Modport, IntfPort, create_intf_port, get_intf_param_string
from .signal import Signal
from .intc import IntcBase
from peakrdl_socgen import module

class AdaptersPath:

    def __init__(self,
                 adapt_from : IntfPort,
                 adapt_to   : IntfPort,
                 rdlc       : RDLCompiler,
                 ):

        self.rdlc = rdlc
        self.adapt_from = adapt_from
        self.adapt_to = adapt_to

        self.adapters = self.createAdaptersOnPath()

    @property
    def intfChain(self) -> "List[IntfPort]":
        l = [self.adapt_from]
        assert self.adapters is not None
        for adapter in self.adapters[:-1]:
            l.append(adapter.mst_port)

        l.append(self.adapt_to)
        return l

    def createAdaptersOnPath(self):
        available_adapters = ["axi2axil", "axil2apb", "nmi2apb", "obi2axil", "obi2axi", "obi2apb"] # TODO find it automatically
        adapter_paths = []

        if self.adapt_from.type == self.adapt_to.type: # TODO different parameters
            return None


        adapter_name = None
        if self.adapt_from.modport.name == "master":
            adapter_name =  self.adapt_from.type.replace("_intf_node", "") + "2" + self.adapt_to.type.replace("_intf_node", "")
        elif self.adapt_from.modport.name == "slave":
            adapter_name = self.adapt_from.type.replace("_intf_node", "") + "2" + self.adapt_to.type.replace("_intf_node", "")

        if adapter_name in available_adapters:
            return [self.createAdapter(
                    ad_type=adapter_name,
                    adapt_from=self.adapt_from,
                    end_intf=self.adapt_to,
                    )]

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

        adapters = []
        for cnt, adapter in enumerate(adapter_paths[0]): # IF master TODO slave
            if cnt == 0:
                adapter = self.createAdapter(
                        ad_type=adapter,
                        adapt_from=self.adapt_from,
                        end_intf=self.adapt_to,
                        )

                adapt_to = create_intf_port(
                        rdlc=self.rdlc,
                        module=adapter,
                        intf_struct=adapter.mst_port.params
                        )
                adapters.append(adapter)

            elif cnt == len(adapter_paths[0]) - 1:
                adapter = self.createAdapter(
                        ad_type=adapter,
                        adapt_from=adapt_to,
                        end_intf=self.adapt_to,
                        )
                adapters.append(adapter)


        assert len(adapter_paths) > 0, f"Could not find appropriate adapter or combination for {intf.type} modport: {intf.modport} and {intc_intf.type}"

        return adapters


    def createAdapter(self,
                      ad_type : str,
                      adapt_from : IntfPort,
                      end_intf : IntfPort,
                      ):


        # Get adapter to extract interface parameters
        inst_name = ad_type + "_" + adapt_from.module.node.get_path().replace(".", "_") + "2" + end_intf.module.node.get_path().replace(".", "_") + "_" 
        adapter = self.rdlc.elaborate(
                top_def_name=ad_type,
                inst_name=inst_name
                ).get_child_by_name(inst_name)

        # Override all matching integer parameters from adapt_from to SLV_INTF parameter
        override_slv_intf, slv_intf_type = {}, None
        override_mst_intf, mst_intf_type = {}, None
        for p in adapter.inst.parameters:
            if isinstance(p.get_value(), UserStruct):
                if p.name == "SLV_INTF":
                    slv_intf_type = p.param_type.__qualname__
                    slv_intf = p.get_value().members
                    for k, v in slv_intf.items():
                        if isinstance(v, int) and not isinstance(v, bool):
                            override_slv_intf[k] = adapt_from.__getattribute__(k) 
                        else:
                            override_slv_intf[k] = slv_intf[k]
                elif p.name == "MST_INTF":
                    mst_intf_type = p.param_type.__qualname__
                    mst_intf = p.get_value().members
                    for k, v in mst_intf.items():
                        if isinstance(v, int) and not isinstance(v, bool):
                            if k in end_intf.params.members:
                                override_mst_intf[k] = end_intf.__getattribute__(k) 
                            else:
                                override_mst_intf[k] = mst_intf[k]
                        else:
                            override_mst_intf[k] = mst_intf[k]

                    pass

        # Override the parameters and create a new adapter node
        slv_intf_param_str = get_intf_param_string(
                intf_type=slv_intf_type,
                intf_dict=override_slv_intf
                )
        slv_intf_param = self.rdlc.eval(slv_intf_param_str)

        mst_intf_param_str = get_intf_param_string(
                intf_type=mst_intf_type,
                intf_dict=override_mst_intf
                )
        mst_intf_param = self.rdlc.eval(mst_intf_param_str)

        adapter = self.rdlc.elaborate(
                top_def_name=ad_type,
                inst_name=inst_name,
                parameters={'SLV_INTF' : slv_intf_param,
                            'MST_INTF' : mst_intf_param,
                            }
                ).get_child_by_name(inst_name)


        return Adapter(
                rdlc=self.rdlc,
                module_node=adapter,
                end_intf=end_intf,

                )

 
class Adapter(Module):
    def __init__(self, 
            rdlc : RDLCompiler,
            module_node : AddrmapNode,
            end_intf : IntfPort,
            ):
        self.rdlc = rdlc

        self.node = module_node
        self.end_intf = end_intf

        super().__init__(self.node, self.rdlc) # type: ignore

    @property
    def slv_port(self) -> IntfPort:
        slaves = [intf for intf in self.intfs if intf.modport.name == "slave"]
        assert len(slaves) == 1, f"Must have only one slave port, {self.node.orig_type_name}"
        return slaves[0]

    @property
    def mst_port(self) -> IntfPort:
        masters = [intf for intf in self.intfs if intf.modport.name == "master"]
        assert len (masters) == 1, f"Must have only one master port, {self.node.orig_type_name}, len: {len(masters)}"
        return masters[0]

    @property
    def intfs(self):
        intfs = []
        for c in self.getAddrmaps():

            intfs.append(IntfPort(
                    rdlc=self.rdlc,
                    port_node=c,
                    module=self,
                    orig_intf=self.end_intf,
                    ))
        return intfs

    def create_ports(self):
        return self.intfs

    # def adapterDrivesExtPort(self):
    #     return self.ext_port.modport == Modport.master
    #
    # def getLeftIntf(self):
    #     if self.adapt_from.modport == Modport.master:
    #         return self.getSlaveIntfs()[0]
    #
    # def getRightIntf(self):
    #     if self.adapt_to.modport == Modport.master:
    #         return self.getMasterIntfs()[0]
    #
    #
    # @property
    # def otherExtPort(self):
    #     if self.adapterDrivesExtPort():
    #         return self.getSlaveIntfs()[0]
    #     else:
    #         return self.getMasterIntfs()[0]
    #
    # # def isDriver(self, s : Signal, intf : Intf):
    # #     if intf not in [self.ext_port]:
    # #         assert False, f"Interface is not connected to interconnect {intf.parent_node.inst_name}_{intf.sig_prefix}{intf.name}"
    # #
    # #     if self.adapterDrivesExtPort():
    # #         if s.isOnlyMiso():
    # #             return True
    # #         elif s.isOnlyMosi():
    # #             return False
    # #     else:
    # #         if s.isOnlyMiso():
    # #             return False
    # #         elif s.isOnlyMosi():
    # #             return True
    # #
    # #     assert False, f"Interface is not connected to interconnect {intf.parent_node.inst_name}_{intf.sig_prefix}{intf.name}"
