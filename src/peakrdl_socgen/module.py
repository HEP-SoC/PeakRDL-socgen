from systemrdl import RDLCompiler
from systemrdl.node import AddrmapNode
from systemrdl.core.parameter import Parameter
from typing import List
import math

from systemrdl.rdltypes.array import ArrayedType

from .intf import Intf, Modport, create_intf_port
from .signal import Signal

class Module:
    def __init__(self,
            node : AddrmapNode,
            rdlc : RDLCompiler
            ):
        self.node = node 
        self.rdlc = rdlc

        self.ports = self.create_ports()

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

    def getOrigTypeName(self) -> str:
        if self.node.orig_type_name is not None:
            return self.node.orig_type_name
        else:
            return self.node.inst_name

    def getSignals(self):
        signals =[]
        for s in self.node.signals():
            if s.get_property("input") or s.get_property("output") or s.get_property("signal_type"):
                signals.append(Signal(s))
        return signals

    def hasSignal(self, sig_name) -> bool:
        for s in self.signals:
            if s.name == sig_name:
                return True
        return False

    def getClkOrRst(self, s : Signal):
        if s.isClk():
            return self.getClk()
        if s.isRst():
            return self.getRst()

    def getClk(self):
        clks = [clk for clk in self.signals if clk.isClk()]
        return clks[0] if len(clks) > 0 else None

    def getRst(self):
        rsts = [rst for rst in self.signals if rst.isRst()]
        return rsts[0] if len(rsts) > 0 else None

    def getAddrmaps(self):
        return [addrmap for addrmap in self.node.children() if isinstance(addrmap, AddrmapNode)]

    def getSlaveNodes(self):
        return [addrmap for addrmap in self.getAddrmaps() if addrmap.get_property('master') is None]

    def getSlavePorts(self) -> List[Intf]:
        return [intf for intf in self.ports if intf.modport.name == "slave"]

    def getMasterPorts(self) -> List[Intf]:
        return [intf for intf in self.ports if intf.modport.name == "master"]

    # def hasIntf(self, intf : Intf):
    #     return intf in self.ports

    def getHdlParameters(self):
        params = [param for param in self.node.inst.parameters if self.isHwParam(param)]

        hw_params = []
        for cnt, param in enumerate(params):
            if isinstance(param.param_type, ArrayedType) and param.param_type.element_type == int:
                param_tmp = {'name': param.name, 'value': self.paramIntArrayToStr(param.get_value())}
            elif param.param_type == str:
                param_tmp = {'name' : param.name, 'value' : '""' if param.get_value() == "" else param.get_value()}
            else:
                param_tmp = {'name': param.name, 'value': param.get_value()}
            hw_params.append(param_tmp)

        return hw_params

    def paramIntArrayToStr(self, array : List[int]) -> str:

        addrw = 32 # TODO
        hexf = math.ceil(addrw//4)

        param = "{"
        for cnt, val in enumerate(array):
            param +=  f" {addrw}'h{val:0{hexf}x}"
            if cnt < len(array)-1:
                param += ", "
        param += "}"
        return param

    def isHwParam(self, param : Parameter):
        # if param.param_type == str and param.name == "INIT_FILE":
        if param.param_type == str and param.name.startswith("SOCGEN_"):
        # if param.param_type == str:
            return True

        return isinstance(param.get_value(), int) or \
               (isinstance(param.param_type, ArrayedType) and param.param_type.element_type == int)

    def getSigVerilogName(self, s : Signal, intf : "Intf | None" = None) -> str:
        return self.node.inst_name + "_" + s.name

    def create_ports(self):
        intfs_prop = self.node.get_property("ifports", default=[])
        axi_intfs  = self.node.get_property("axi_intfs", default=[])
        axil_intfs  = self.node.get_property("axil_intfs", default=[])
        apb_intfs  = self.node.get_property("apb_intfs", default=[])
        obi_intfs  = self.node.get_property("obi_intfs", default=[])
        nmi_intfs  = self.node.get_property("nmi_intfs", default=[])
        all_intf_props = intfs_prop + axi_intfs + axil_intfs + apb_intfs + obi_intfs + nmi_intfs

        if all_intf_props is None:
            return []
        ports = []
        for p in all_intf_props:
            port = create_intf_port(
                    rdlc=self.rdlc,
                    module=self,
                    intf_struct=p
                    )
            ports.append(port)

        return ports
