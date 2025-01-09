from typing import List, Optional
from systemrdl import RDLCompiler
from systemrdl.node import AddrmapNode
from systemrdl.rdltypes import UserStruct
from .module import Module
from .intf import IntfPort

class AdaptersPath:
    """This class is used to find the adapter path from one to another
    interface type using a set of fixed adapters.
    """
    def __init__(self,
                 adapt_from : IntfPort,
                 adapt_to   : IntfPort,
                 rdlc       : RDLCompiler,
                 intc_prefix: str="",
                 ):

        self.rdlc = rdlc
        self.adapt_from = adapt_from
        self.adapt_to = adapt_to

        self.intc_prefix = intc_prefix

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
         # TODO find this list automatically
        available_adapters = ["axi2axil", "axil2apb", "nmi2apb", "obi2axil", "obi2axi", "obi2apb", "obi2apb_rt",  "obiTMR2obi",
            "obiTMR2apb_rt", "apb2apb_rt", "apb_rt2apb"]
        adapter_paths = []

        if self.adapt_from.type == self.adapt_to.type: # TODO check if different parameters
            return None

        adapter_name = None
        # Create the adapter name using the two interface types (e.g., obi_intf_node and apb_intf_node -> obi2apb)
        if self.adapt_from.modport.name == "master":
            adapter_name = self.adapt_from.type.replace("_intf_node", "") + "2" + self.adapt_to.type.replace("_intf_node", "")
        elif self.adapt_from.modport.name == "slave":
            adapter_name = self.adapt_from.type.replace("_intf_node", "") + "2" + self.adapt_to.type.replace("_intf_node", "")

        # If a direct adapter exist return it
        if adapter_name in available_adapters:
            return [self.createAdapter(
                    ad_type=adapter_name,
                    adapt_from=self.adapt_from,
                    adapt_to=self.adapt_to,
                    )]

        # Find a different path if direct adapter does not exist (not extensively tested)
        fitting_slaves = []
        fitting_masters = []
        for a in available_adapters:
            if a.split("2")[0] == adapter_name.split("2")[0]: # type: ignore
                fitting_slaves.append(a)

            if a.split("2")[1] == adapter_name.split("2")[1]: # type: ignore
                fitting_masters.append(a)

        adapter_paths = []
        # Maximum path length is two adapters currently
        for slv in fitting_slaves:
            for mst in fitting_masters:
                if slv.split("2")[1] == mst.split("2")[0]:
                    adapter_paths.append([slv, mst])

        assert len(adapter_paths) > 0, f"Could not find appropriate adapter or combination from {self.adapt_from.type} to {self.adapt_to.type}"

        adapters = []

        for cnt, adapter in enumerate(adapter_paths[0]): # IF master TODO slave
            if cnt == 0:
                adapter = self.createAdapter(
                        ad_type=adapter,
                        adapt_from=self.adapt_from,
                        adapt_to=self.adapt_to,
                        )

                adapt_to = IntfPort.create_intf_port(
                        rdlc=self.rdlc,
                        module=adapter,
                        intf_struct=adapter.mst_port.params
                        )
                # IntfPort.create_intf_port() returns a list, for adapters it should always return a single intf port
                assert len(adapt_to) == 1, f"Assert adapter interface port returned more than one port."
                adapt_to = adapt_to[0]

                adapters.append(adapter)

            elif cnt == len(adapter_paths[0]) - 1:
                adapter = self.createAdapter(
                        ad_type=adapter,
                        adapt_from=adapt_to,
                        adapt_to=self.adapt_to,
                        )
                adapters.append(adapter)

        return adapters


    def createAdapter(self, ad_type: str, adapt_from: IntfPort, adapt_to: IntfPort) -> 'Adapter':
        """Returns and Adapter handle for the given ports."""

        # Generate a unique instance name
        # TODO Change the generated name to something more clear (now it uses the first found slave by default for adapt_from)
        inst_name = ad_type # + "_" + adapt_from.module.node.get_path().replace(".", "_") + "2" + adapt_to.module.node.get_path().replace(".", "_")
        if self.intc_prefix:
            inst_name += "_" + self.intc_prefix
        # Elaborate the interface SystemRDL compiler, overrides the adapter instance name,
        # and get the addrmap no handle by getting the root node child
        adapter_node = self.rdlc.elaborate(
                top_def_name=ad_type,
                inst_name=inst_name
                ).get_child_by_name(inst_name)

        # Override all matching integer parameters from adapt_from interface to SLV_INTF parameter
        override_slv_intf, slv_intf_type = {}, None
        override_mst_intf, mst_intf_type = {}, None
        for p in adapter_node.inst.parameters:
            # Look for the structure parameters
            if isinstance(p.get_value(), UserStruct):
                if p.name == "SLV_INTF":
                    slv_intf_type = p.param_type.__name__
                    # Get the structure members
                    slv_intf = p.get_value().members
                    for k, v in slv_intf.items():
                        if isinstance(v, int) and not isinstance(v, bool):
                            override_slv_intf[k] = adapt_from.__getattribute__(k)
                        else: # bool, str, custom type
                            override_slv_intf[k] = slv_intf[k]
                elif p.name == "MST_INTF":
                    mst_intf_type = p.param_type.__qualname__
                    mst_intf = p.get_value().members
                    for k, v in mst_intf.items():
                        if isinstance(v, int) and not isinstance(v, bool):
                            if k in adapt_to.params.members:
                                override_mst_intf[k] = adapt_to.__getattribute__(k)
                            else:
                                # Use default value if not found in adapt_to node
                                override_mst_intf[k] = mst_intf[k]
                        else: # bool, str, custom type
                            override_mst_intf[k] = mst_intf[k]

        # Generate the struct parameter string for the slave interface
        slv_intf_param_str = IntfPort.get_intf_param_string(
                intf_type=slv_intf_type,
                intf_dict=override_slv_intf
                )
        # Convert the structure parameter string to a SystemRDL struct object
        slv_intf_param = self.rdlc.eval(slv_intf_param_str)

        # Generate the struct parameter string for the master interface
        mst_intf_param_str = IntfPort.get_intf_param_string(
                intf_type=mst_intf_type,
                intf_dict=override_mst_intf
                )
        # Convert the structure parameter string to a SystemRDL struct object
        mst_intf_param = self.rdlc.eval(mst_intf_param_str)

        # Override the generic parameters of the adapter and create a new adapter node
        adapter_node = self.rdlc.elaborate(
                top_def_name=ad_type,
                inst_name=inst_name,
                parameters={'SLV_INTF': slv_intf_param,
                            'MST_INTF': mst_intf_param,
                            }
                ).get_child_by_name(inst_name)

        # Set the adapter address offset to the original AddrmapNode one
        adapter_node.inst.addr_offset = adapt_to.module.node.inst.addr_offset

        # Return an Adapter object handle containing the adapter node
        # We need to pass the original AddrmapNode size to the adapter to create the correct address map package for the SoC
        # We cannot modify the size attribute like the addr_offset so it is passed as an argument to the adapter
        return Adapter(rdlc=self.rdlc, module_node=adapter_node, end_intf=adapt_to, addr_map_size=adapt_to.module.size)


class Adapter(Module):
    """This classe is a wrapper around an adapter node (i.e., an addrmap) converting
    a bus protocol to a different one (e.g., obi <-> apb). This class extend the base
    Module class used to represent a verilog module.
    """
    def __init__(self,
            rdlc: RDLCompiler,
            module_node: AddrmapNode,
            end_intf: IntfPort,
            addr_map_size: Optional[int] = None
            ):
        self.rdlc = rdlc

        self.node = module_node
        self.end_intf = end_intf

        if addr_map_size is None:
            self.addr_map_size = module_node.size
        else:
            self.addr_map_size = addr_map_size

        super().__init__(self.node, self.rdlc) # type: ignore

    @property
    def size(self) -> int:
        return self.addr_map_size

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
                    port_node=c,
                    module=self,
                    orig_intf=self.end_intf,
                    ))
        return intfs

    @property
    def end_node_name(self):
        # If another adapter has been added skip it until we reach the base module
        if self.end_intf.module.node.get_property("adapter"):
            return self.end_intf.module.end_node_name
        else:
            return self.end_intf.module.node.inst_name
