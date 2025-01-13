from systemrdl import RDLCompiler, RDLListener
from systemrdl.node import AddrmapNode
from typing import List
import logging
import re

from .signal import Signal
from .module import Module
from .intf import IntfPort
from .intc import Intc
from .adapter import AdaptersPath

# Logger generation for halnode module
subsys_logger = logging.getLogger("subsys_logger")
# Console handler
ch = logging.StreamHandler()
# create formatter and add it to the handlers
formatter = logging.Formatter('%(name)s - %(levelname)s: %(message)s')
ch.setFormatter(formatter)
# add the handlers to the logger
subsys_logger.addHandler(ch)
# Set for more verbosity
subsys_logger.setLevel(logging.INFO)

class SubsystemListener(RDLListener):
    """This class extend the RDLListener to extract the subsystem nodes (i.e., the
    nodes with the subsytem property set).
    """
    def __init__(self):
        self.subsystem_nodes = []

    def enter_Addrmap(self, node):
        """Executed when entering an addrmap node."""
        if node.get_property("subsystem") is not None:
            self.subsystem_nodes.append(node)

class Subsystem(Module): # TODO is module and subsystem the same?
    """This class extend the Module class for subsytem (i.e., generated module)."""
    def __init__(self, node: AddrmapNode, rdlc: RDLCompiler):
        super().__init__(node, rdlc)

        # List of all addrmap childrens (either with a Module or a Subsystem handle)
        self.modules = self.getModules()

        # List of module's children master ports and module's slave ports
        self.initiators = self.getInitiators()
        # List of module's children slave ports and module's master ports
        self.endpoints = self.getEndpoints()

        self.adapter_paths = []

        # First get the user defined ones to remove them from the initiators and endpoints lists
        self.intcs = self.getUserDefinedIntcs()
        # Then append the default interconnect built from the remaining initiatiors and endpoints
        self.intcs.append(self.create_intc(self.initiators, self.endpoints))


    def getAllModules(self) -> List[Module]:
        """Returns the child modules, interconnects, and adapters."""
        mods = self.modules + self.intcs + self.getAllAdapters()
        return mods

    def getAllAdapters(self):
        """Returns the interconnect adapters."""
        adapters = []
        for ap in self.adapter_paths:
            adapters.extend(ap.adapters)
        return adapters

    def getUserDefinedIntcs(self):
        """Returns the list of interconnects explicitely defined.

        By default, SoCgen assume a single unified bus interconnection. To create multiple
        interconnects, you have to explicitely instantiate the extra ones using the
        'intc_l' property and intc structure inside an addrmap node. For example:

        intc_l = '{
            intc '{
                name:"user_intc",
                slv_ports:'{"<path_to_slave_intf_0>", "<path_to_slave_intf_1>", ...},
                mst_ports:'{"<path_to_master_intf_0>", "<path_to_master_intf_1>", ...},
            }
        };
        """
        intcs = []
        intc_l = self.node.get_property('intc_l', default=[])

        for intc in intc_l:
            ext_mst_ports = []
            ext_slv_ports = []

            for mst in intc.mst_ports:
                intf = self.findPortInChildren(mst)
                # Remove the intf from the default interconnect
                if intf in self.endpoints:
                    self.endpoints.remove(intf)
                ext_mst_ports.append(intf)

            for slv in intc.slv_ports:
                intf = self.findPortInChildren(slv)
                # Remove the intf from the default interconnect
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


    def findPortInChildren(self, string: str) -> IntfPort:
        """Returns an interface port handler with a name matching the given string.

        For example, you have the following user defined interconnect in your addrmap node:

        addrmap my_addrmap
        {
            ...
            intc_l = '{
                intc '{
                    name:"user_intc",
                    slv_ports:'{"slv_module0.slv_port_", "slv_module1.slv_port_"},
                    mst_ports:'{"mst_module0.mst_port_", "mst_module1.mst_port_"},
                }
            };
            ...
        };

        In your slave/master module addrmap nodes you must define an interface with the
        prefix 'slv_port_'/'mst_port_'. For example:

        addrmap slv_module0 #(
            obi_intf INTF = obi_intf'{
                ADDR_WIDTH:32,
                DATA_WIDTH:32,
                prefix:"slv_port_",
                modport:Modport::slave,
                cap:false
            }
        ){
            ...
            ifports = '{INTF};
            ...
        };

        """
        for intf in self.getChildPorts():
            # Get the relative path of the intf from this module
            node_rel = intf.module.node.get_path().replace(self.node.get_path() + ".", "")
            if (node_rel + "." + intf.prefix) == string:
                return intf
        assert False, f"Could not find interface {string}"

    def getModules(self):
        """Returns Module or Subsystem objects from node addrmap children."""
        modules = []
        for node in self.getAddrmaps():
            if node.get_property('subsystem'):
                modules.append(Subsystem(node, self.rdlc))
            else:
                modules.append(Module(node, self.rdlc))

        return modules

    def getMatchingClk(self, m: Module, s: Signal) -> Signal:
        """Returns a clock Signal object handle."""
        subsys_clks = self.getClks()
        module_clks = m.getClks()
        if len(subsys_clks) == 1:
            # If there is only one clock, use that
            # Issue a warning if the module to instantiate has multiple instead
            if len(module_clks) > 1:
                subsys_logger.warning(f'Current subsystem {self.getOrigTypeName()} only has one clock, but {m.getOrigTypeName()} has multiple. Connecting clock: {self.getOrigTypeName()}.{subsys_clks[0].name} to: {m.getOrigTypeName()}.{s.name}')
            return subsys_clks[0]
        else:
            for clk in subsys_clks:
                # First try an exact name match
                if clk.name == s.name:
                    subsys_logger.info(f'Clock with matching name found. Connecting clock: {self.getOrigTypeName()}.{subsys_clks[0].name} to: {m.getOrigTypeName()}.{s.name}')
                    return clk
                # Then match last character if subsystem and module have the same number of clocks (e.g for A, B, C or 1, 2, 3)
                if len(subsys_clks) == len(module_clks) and clk.name[-1] == s.name[-1]:
                    subsys_logger.info(f'Matching clock found on last character. Connecting clock: {self.getOrigTypeName()}.{subsys_clks[0].name} to: {m.getOrigTypeName()}.{s.name}')
                    return clk
            else:
                subsys_logger.warning(f'No matching clock found, using the first as default. Connecting clock: {self.getOrigTypeName()}.{subsys_clks[0].name} to: {m.getOrigTypeName()}.{s.name}')
                return subsys_clks[0]

    def getMatchingRst(self, m: Module, s: Signal) -> Signal:
        """Returns a reset Signal object handle."""
        subsys_rsts = self.getRsts()
        module_rsts = m.getRsts()
        if len(subsys_rsts) == 1:
            # If there is only one reset, use that
            # Issue a warning if the module to instantiate has multiple instead
            if len(module_rsts) > 1:
                subsys_logger.warning(f'Current subsystem {self.getOrigTypeName()} only has one reset, but {m.getOrigTypeName()} has multiple. Connecting reset: {self.getOrigTypeName()}.{subsys_rsts[0].name} to: {m.getOrigTypeName()}.{s.name}')
            return subsys_rsts[0]
        else:
            for rst in subsys_rsts:
                # First try an exact name match
                if rst.name == s.name:
                    subsys_logger.info(f'Reset with matching name found. Connecting reset: {self.getOrigTypeName()}.{subsys_rsts[0].name} to: {m.getOrigTypeName()}.{s.name}')
                    return rst
                # Then match last character if subsystem and module have the same number of resets (e.g for A, B, C or 1, 2, 3)
                if len(subsys_rsts) == len(module_rsts) and rst.name[-1] == s.name[-1]:
                    subsys_logger.info(f'Matching reset found on last character. Connecting reset: {self.getOrigTypeName()}.{subsys_rsts[0].name} to: {m.getOrigTypeName()}.{s.name}')
                    return rst
            else:
                subsys_logger.warning(f'No matching reset found, using the first as default. Connecting reset: {self.getOrigTypeName()}.{subsys_rsts[0].name} to: {m.getOrigTypeName()}.{s.name}')
                return subsys_rsts[0]

    def getMatchingSignal(self, submodule: Module, submodule_signal: Signal) -> Signal:
        subsys_logger.debug(f"Subsystem {self.node.inst_name} - getMatchingSignal: {self.node.inst_name} has {submodule_signal.name}?")

        # Create signal full path to check
        submodule_signal_path = f"{submodule.node.inst_name}.{submodule_signal.name}"

        # Check explicit port signals
        for s in self.port_signals:
            # explicit port signal contains the 'path' property to give the connection path from/to it
            path = s.node.get_property("path", default="")
            path_list = path.split(';')
            # We compare also against s.name (compared to hasConnection) because here we can use the internal
            # signals to make the connection
            if submodule_signal.name == s.name:
                subsys_logger.debug(f"Yes (explicit port signal)")
                return s
            for p in path_list:
                if p == submodule_signal_path:
                    return s

        # Regex pattern to check if signal name is present or not in the submodule
        # The signal is check independently of the standard port naming conventions
        regex_pattern = rf"^{re.escape(submodule_signal_path)}"

        # Check internal signals
        for s in self.internal_signals:
            subsys_logger.debug(f"Subsystem - getMatchingSignal: checking internal signal {s.name}")
            # Check the full path name
            to_path = s.node.get_property("to", default="")
            to_path_list = to_path.split(';')
            from_path = s.node.get_property("from", default="")
            subsys_logger.debug(f"Subsystem - getMatchingSignal: internal signal to_path: {to_path}")
            subsys_logger.debug(f"Subsystem - getMatchingSignal: internal signal from_path: {from_path}")
            # Check the full from path
            if re.fullmatch(regex_pattern, from_path):
                subsys_logger.debug(f"Yes (internal from_path signal)")
                return s
            # Check to paths
            for p in to_path_list:
                if re.fullmatch(regex_pattern, p):
                    subsys_logger.debug(f"Yes (internal to_path signal)")
                    return s

        assert False, f"The subsystem submodule {submodule.node.inst_name} does not contain the signal {submodule_signal.name}"

    def hasConnection(self, submodule: Module, submodule_signal: Signal) -> bool:
        """Returns True if the module has a connection signal matching the given one."""
        subsys_logger.debug(f"Subsystem {self.node.inst_name}/{submodule.node.inst_name} - hasConnection: {self.node.inst_name} has {submodule_signal.name} connected to a module?")

        # Create signal full path to check
        submodule_signal_path = f"{submodule.node.inst_name}.{submodule_signal.name}"

        # Check explicit port signals
        for s in self.port_signals:
            # explicit port signal contains the 'path' property to give the connection path from/to it
            path = s.node.get_property("path", default="")
            path_list = path.split(';')
            # We don't check against s.name directly (compared to getMatchingSignal) because we don't
            # want a connection just because the subsystem as a port with the same name than one of its
            # submodules
            if submodule_signal_path in path_list:
                subsys_logger.debug(f"Yes (explicit port signal)")
                return True


        # Regex pattern to check if signal name is present or not in the submodule
        # The signal is check independently of the standard port naming conventions
        regex_pattern = rf"^{re.escape(submodule_signal_path)}(_(ni|nio|i|o|io|no))?$"

        # Check internal signals
        for s in self.internal_signals:
            subsys_logger.debug(f"Subsystem - hasConnection: checking internal signal {s.name}")
            # Keep only the ultimate path name
            to_path = s.node.get_property("to", default="")
            to_path_list = to_path.split(';')
            from_path = s.node.get_property("from", default="")
            # Check from paths
            if re.fullmatch(regex_pattern, from_path):
                subsys_logger.debug(f"Yes (internal from_path signal)")
                return True
            # Check to paths
            for p in to_path_list:
                if re.fullmatch(regex_pattern, p):
                    subsys_logger.debug(f"Yes (internal to_path signal)")
                    return s

        subsys_logger.debug(f"No")
        return False

    def getEndpoints(self) -> List[IntfPort]:
        """Returns a list of children module/subsystem slave ports and subsystem master ports."""
        # Get all the slave ports of the children modules and subsystems
        endpoints = [intf for module in self.modules for intf in module.getSlavePorts()]
        # Add the master ports of the current subsystem
        endpoints.extend(self.getMasterPorts()) # WHY?
        return endpoints

    def getInitiators(self) -> List[IntfPort]:
        """Returns a list of children module/subsystem master ports and subsystem slave ports."""
        # Get all the master ports of the children modules and subsystems
        initiators = [intf for module in self.modules for intf in module.getMasterPorts()]
        # Add the slave ports of the current subsystem
        initiators.extend(self.getSlavePorts()) # WHY?
        return initiators

    def getPorts(self) -> List[IntfPort]:
        return self.getEndpoints() + self.getInitiators()

    def getChildPorts(self):
        """Returns the module children ports."""
        return [port for module in self.modules for port in module.ports]

    def create_intc(self,
                    slv_ports: List[IntfPort],
                    mst_ports: List[IntfPort],
                    inst_prefix: str="",
                    ) -> Intc:

        # Get the most used interface from slave ports (slave from the interconnect point of view)
        # All slaves must be identical
        # TODO add adapter for slave ports too
        intf_type = slv_ports[0].type
        # Check all slaves are similar
        ports_need_adapter = [port for port in slv_ports if port.type != intf_type]
        assert ports_need_adapter == [], f"Different types of interconnect slave ports is not supported for now."

        # Check if all the master ports have the same type or if adapter(s) is needed
        ports_need_adapter = [port for port in mst_ports if port.type != intf_type]

        for p in ports_need_adapter:
            self.adapter_paths.append(AdaptersPath(
                    adapt_from=slv_ports[0], # For now all slaves are identical
                    adapt_to=p,
                    rdlc=self.rdlc,
                    intc_prefix=inst_prefix
                    )
                  )

            for cnt, mst_p in enumerate(mst_ports):
                if mst_p == p:
                    # Find the corresponding master port (i.e., going to slave block)
                    # and change it to the last created AdapterPath's first adapter slave port
                    # !!! A master port get assigned a slave port (i.e., modport == 'slave') !!!
                    # TODO Find a less error prone alternative -> actually this helps for the below assertion check
                    mst_ports[cnt] = self.adapter_paths[-1].adapters[0].slv_port

        # Check all the ports originate from this subsystem
        for p in slv_ports:
            # Check the port mode to avoid checking adapters which are only connected internally
            if p.modport.name == "slave":
                assert p.module.node == self.node, f"Interface port {p} is slave but is not a port of the subsystem node"

        for p in mst_ports:
            # Check the port mode to avoid checking adapters which are only connected internally
            if p.modport.name == "master":
                assert p.module.node == self.node, f"Interface port {p} is master but is not a port of the subsystem node"

        # At that point all ports have the same type
        return Intc(
                rdlc=self.rdlc,
                ext_slv_ports=slv_ports,
                ext_mst_ports=mst_ports,
                subsystem_node=self.node,
                inst_prefix=inst_prefix,
                )
