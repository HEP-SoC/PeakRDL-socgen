# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2025 CERN
#
# Please retain this header in all redistributions and modifications of the code.

from systemrdl import RDLCompiler
from systemrdl.node import AddrmapNode
from systemrdl.core.parameter import Parameter
from typing import List
import math
import logging
import re

from systemrdl.rdltypes.array import ArrayedType

from .intf import IntfPort
from .signal import Signal

# Logger generation for halnode module
module_logger = logging.getLogger("module_logger")
# Console handler
ch = logging.StreamHandler()
# create formatter and add it to the handlers
formatter = logging.Formatter('%(name)s - %(levelname)s: %(message)s')
ch.setFormatter(formatter)
# add the handlers to the logger
module_logger.addHandler(ch)

# Set for more verbosity
module_logger.setLevel(logging.INFO)

class Module:
    def __init__(self, node: AddrmapNode, rdlc: RDLCompiler):
        """Each module is a wrapper around an AddrmapNode and contains an RDLCompiler
        with the interface files."""
        self.node = node
        self.rdlc = rdlc

        self.ports = self.create_ports()

        self.hdl_params = self._getHdlParameters()

        self.port_signals, self.internal_signals = self.getSignals()

    @property
    def isOnlyMaster(self) -> bool:
        for p in self.ports:
            if p.params.modport.name == "slave":
                return False
        return True

    @property
    def isOnlySlave(self) -> bool:
        for p in self.ports:
            if p.params.modport.name == "master":
                return False
        return True

    @property
    def size(self) -> int:
        return self.node.size

    def getOrigTypeName(self) -> str:
        if self.node.orig_type_name is not None:
            return self.node.orig_type_name
        else:
            return self.node.inst_name

    def getSignals(self):
        port_signals = []
        internal_signals = []
        for s in self.node.signals():
            if s.get_property("input") or s.get_property("output") or s.get_property("inout"):
                port_signals.append(Signal(s))
                module_logger.debug(f"Module {self.node.inst_name} - getSignals: added signal {port_signals[-1].name} to port_signals of module {self.node.inst_name}")
            else:
                internal_signals.append(Signal(s))
                module_logger.debug(f"Module {self.node.inst_name} - getSignals: added signal {internal_signals[-1].name} to internal_signals of module {self.node.inst_name}")
        return port_signals, internal_signals

    def hasSignal(self, sig_name) -> bool:
        """Returns True if the module has a signal matching the given one."""
        module_logger.debug(f"Module - hasSignal: {self.node.inst_name} has {sig_name}?")
        # Check explicit port signals
        for s in self.port_signals:
            if s.name == sig_name:
                module_logger.debug(f"Yes (explicit port signal)")
                return True
        # Check internal signals
        for s in self.internal_signals:
            module_logger.debug(f"Module - hasSignal: checking internal signal {s.name}")
            # Keep only the ultimate path name
            to_path = s.node.get_property("to", default="").split('.')[-1]
            from_path = s.node.get_property("from", default="").split('.')[-1]
            # Regex pattern to check if signal name is present or not in the module
            # The signal is check independently of the standard port naming conventions
            regex_pattern = rf"^{re.escape(sig_name)}(_(ni|nio|i|o|io|no))?$"
            if re.fullmatch(regex_pattern, to_path) or re.fullmatch(regex_pattern, from_path):
                module_logger.debug(f"Yes (internal signal)")
                return True

        module_logger.debug(f"No")
        return False
        # Skip warning for clock and reset as they are instantiated separately
        # # We only have the signal name so to a simple filtering
        # if 'clk' not in sig_name and 'rst' not in sig_name:
        #     module_logger.warning(f"Module {self.getOrigTypeName()} has no signal {sig_name} (ignore if signal linked through 'path')")
        # return False

    def getClks(self) -> Signal:
        """Returns a list of clock Signal object handles."""
        clks = [clk for clk in self.port_signals if clk.isClk()]
        if len(clks) > 0:
            return clks
        else:
            module_logger.error(f'No clock found in module {self.getOrigTypeName()}.')
            return None

    def getRsts(self):
        """Returns a list of reset Signal object handles."""
        rsts = [rst for rst in self.port_signals if rst.isRst()]
        if len(rsts) > 0:
            return rsts
        else:
            module_logger.error(f'No reset found in module {self.getOrigTypeName()}.')
            return None

    def getAddrmaps(self):
        """Returns the children of type addrmap."""
        return [addrmap for addrmap in self.node.children() if isinstance(addrmap, AddrmapNode)]

    def getSlavePorts(self) -> List[IntfPort]:
        """Returns module slave ports."""
        return [intf for intf in self.ports if intf.modport.name == "slave"]

    def getMasterPorts(self) -> List[IntfPort]:
        """Returns module master ports."""
        return [intf for intf in self.ports if intf.modport.name == "master"]

    def _getHdlParameters(self):
        params = [param for param in self.node.inst.parameters if self.isHwParam(param)]

        hw_params = []
        for cnt, param in enumerate(params):
            if isinstance(param.param_type, ArrayedType) and param.param_type.element_type == int:
                param_tmp = {'name': param.name, 'value': self.paramIntArrayToStr(param.get_value())}
            elif param.param_type == str:
                param_tmp = {'name': param.name, 'value': '""' if param.get_value() == "" else param.get_value()}
            else:
                param_tmp = {'name': param.name, 'value': param.get_value()}
            hw_params.append(param_tmp)

        return hw_params

    def paramIntArrayToStr(self, array: List[int]) -> str:

        addrw = 32 # TODO
        hexf = math.ceil(addrw//4)

        param = "{"
        for cnt, val in enumerate(array):
            param +=  f" {addrw}'h{val:0{hexf}x}"
            if cnt < len(array)-1:
                param += ", "
        param += "}"
        return param

    def isHwParam(self, param: Parameter):
        """Returns True if the parameter starts with 'SOCGEN_' or is an array of integer."""
        if param.param_type == str and param.name.startswith("SOCGEN_"):
            return True

        return isinstance(param.get_value(), int) or \
               (isinstance(param.param_type, ArrayedType) and param.param_type.element_type == int)

    def getSigVerilogName(self, s: Signal) -> str:
        """Returns the module/node instance name appended with the signal instance name."""
        # Used for internal connection within a module, remove any port-specific suffix for better readability
        signal_name = s.name
        module_logger.debug(f"Module {self.node.inst_name} - getSigVerilogName for signal {signal_name}")
        # This function is called only for internal signals, so remove any standard suffix
        # Regex pattern
        match_pattern = r"_(ni|nio|i|o|io|no)([A|B|C]?)$"
        replace_pattern = r"\2"
        if re.search(match_pattern, signal_name):
            # Perform the regex replacement
            signal_name = re.sub(match_pattern, replace_pattern, signal_name)
            module_logger.debug(f"Module {self.node.inst_name} - getSigVerilogName: regex found and replaced: {signal_name}")

        return self.node.inst_name + "_" + signal_name

    def create_ports(self) -> List[IntfPort]:
        """Get the module declared interfaces and create an IntfPort object for each of them.

        To add an interface to an addrmap representing a module (e.g., a memory or a peripheral)
        you have to declare it as follows (here for an apb interface):

            addrmap my_periph #(
                apb_intf INTF = apb_intf'{
                    ADDR_WIDTH:32,
                    DATA_WIDTH:32,
                    prefix:"s_",
                    modport:Modport::slave,
                    cap:false
                }
            ){
                ifports = '{ INTF };
                ...
            };

        ifports or the interface list property (e.g., apb_intfs) will be recognized by this method.
        """
        intfs_prop = self.node.get_property("ifports", default=[])
        axi_intfs  = self.node.get_property("axi_intfs", default=[])
        axil_intfs  = self.node.get_property("axil_intfs", default=[])
        apb_intfs  = self.node.get_property("apb_intfs", default=[])
        obi_intfs  = self.node.get_property("obi_intfs", default=[])
        nmi_intfs  = self.node.get_property("nmi_intfs", default=[])
        apb_rt_intfs  = self.node.get_property("apb_rt_intfs", default=[])
        obiTMR_intfs  = self.node.get_property("obiTMR_intfs", default=[])

        obi_intc_ports = self.node.get_property("obi_intc_ports", default=[])
        apb_intc_ports = self.node.get_property("apb_intc_ports", default=[])
        axi_intc_ports = self.node.get_property("axi_intc_ports", default=[])
        axil_intc_ports = self.node.get_property("axil_intc_ports", default=[])
        nmi_intc_ports = self.node.get_property("nmi_intc_ports", default=[])
        apb_rt_intc_ports = self.node.get_property("apb_rt_intc_ports", default=[])
        obiTMR_intc_ports = self.node.get_property("obiTMR_intc_ports", default=[])

        all_intf_props = intfs_prop + axi_intfs + axil_intfs + apb_intfs + obi_intfs + nmi_intfs + apb_rt_intfs + \
                         obi_intc_ports + apb_intc_ports + axi_intc_ports + axil_intc_ports + nmi_intc_ports + \
                         apb_rt_intc_ports + obiTMR_intfs + obiTMR_intc_ports

        ports = []
        for p in all_intf_props:
            port = IntfPort.create_intf_port(rdlc=self.rdlc, module=self, intf_struct=p)
            ports.extend(port)

        return ports
