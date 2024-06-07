from systemrdl import RDLCompiler
from systemrdl.node import AddrmapNode
from systemrdl.core.parameter import Parameter
from typing import List
import math
import logging

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

class Module:
    def __init__(self, node: AddrmapNode, rdlc: RDLCompiler):
        """Each module is a wrapper around an AddrmapNode and contains an RDLCompiler
        with the interface files."""
        self.node = node
        self.rdlc = rdlc

        self.ports = self.create_ports()

        self.hdl_params = self._getHdlParameters()

        self.signals = self.getSignals()

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
        signals =[]
        for s in self.node.signals():
            if s.get_property("input") or s.get_property("output"):
                signals.append(Signal(s))
        return signals

    def hasSignal(self, sig_name) -> bool:
        """Returns True if the module has a signal matching the given one."""
        for s in self.signals:
            if s.name == sig_name:
                return True
        # Skip warning for clock and reset as they are instantiated separately
        # # We only have the signal name so to a simple filtering
        # if 'clk' not in sig_name and 'rst' not in sig_name:
        #     module_logger.warning(f"Module {self.getOrigTypeName()} has no signal {sig_name} (ignore if signal linked through 'path')")
        # return False

    def getClkOrRst(self, s: Signal) -> Signal:
        """Returns a clock or reset Signal object handle."""
        if s.isClk():
            return self.getClk()
        if s.isRst():
            return self.getRst()

    def getClk(self) -> Signal:
        """Returns a clock Signal object handle."""
        clks = [clk for clk in self.signals if clk.isClk()]
        if len(clks) > 0:
            if len(clks) > 1:
                module_logger.warning(f'Multiple clocks found for module {self.getOrigTypeName()}, using the first found {clks[0].name}')
            return clks[0]
        else:
            module_logger.error(f'No clock found in module {self.getOrigTypeName()}.')
            return None

    def getRst(self):
        """Returns a reset Signal object handle."""
        rsts = [rst for rst in self.signals if rst.isRst()]
        if len(rsts) > 0:
            if len(rsts) > 1:
                module_logger.warning(f'Multiple resets found for module {self.getOrigTypeName()}, using the first found {rsts[0].name}')
            return rsts[0]
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
        return self.node.inst_name + "_" + s.name

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

        obi_intc_ports = self.node.get_property("obi_intc_ports", default=[])
        apb_intc_ports = self.node.get_property("apb_intc_ports", default=[])
        axi_intc_ports = self.node.get_property("axi_intc_ports", default=[])
        axil_intc_ports = self.node.get_property("axil_intc_ports", default=[])
        nmi_intc_ports = self.node.get_property("nmi_intc_ports", default=[])
        apb_rt_intc_ports = self.node.get_property("apb_rt_intc_ports", default=[])

        all_intf_props = intfs_prop + axi_intfs + axil_intfs + apb_intfs + obi_intfs + nmi_intfs + apb_rt_intfs + \
                         obi_intc_ports + apb_intc_ports + axi_intc_ports + axil_intc_ports + nmi_intc_ports + \
                         apb_rt_intc_ports

        ports = []
        for p in all_intf_props:
            port = IntfPort.create_intf_port(rdlc=self.rdlc, module=self, intf_struct=p)
            ports.extend(port)

        return ports
