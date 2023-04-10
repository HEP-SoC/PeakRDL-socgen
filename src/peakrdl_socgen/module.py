from systemrdl import RDLCompiler
from systemrdl.node import AddrmapNode
from systemrdl.core.parameter import Parameter
from typing import List
import math

from systemrdl.rdltypes.array import ArrayPlaceholder

from .intf import Intf, Signal, create_intf, IntfModport

class Module:
    def __init__(self,
            node : AddrmapNode,
            rdlc : RDLCompiler
            ):
        self.node = node 
        self.rdlc = rdlc

        self.intfs = self.get_intfs()

        self.signals = self.getSignals()

    def getOrigTypeName(self) -> str:
        if self.node.orig_type_name is not None:
            return self.node.orig_type_name
        else:
            return self.node.inst_name

    def getSignals(self):
        return [Signal(s) for s in self.node.signals()]

    def getClkOrRst(self, s : Signal):
        if s.isClk():
            return self.getClk()
        if s.isRst():
            return self.getRst()

    def getClk(self):
        return [clk for clk in self.signals if clk.isClk()][0]

    def getRst(self):
        return [rst for rst in self.signals if rst.isRst()][0]

    def getAddrmaps(self):
        return [addrmap for addrmap in self.node.children() if isinstance(addrmap, AddrmapNode)]

    def getSlaveNodes(self):
        return [addrmap for addrmap in self.getAddrmaps() if addrmap.get_property('master') is None]

    def getSlaveIntfs(self) -> List[Intf]:
        return [intf for intf in self.intfs if intf.modport == IntfModport.SLAVE]

    def getMasterIntfs(self) -> List[Intf]:
        return [intf for intf in self.intfs if intf.modport == IntfModport.MASTER]

    def getHdlParameters(self):
        params = [param for param in self.node.inst.parameters if self.isHwParam(param)]

        hw_params = []
        for cnt, param in enumerate(params):
            if isinstance(param.param_type, ArrayPlaceholder) and param.param_type.element_type == int:
                param_tmp = {'name': param.name, 'value': self.paramIntArrayToStr(param.get_value())}
                hw_params.append(param_tmp)
            else:
                param_tmp = {'name': param.name, 'value': param.get_value()}
                hw_params.append(param_tmp)

        return hw_params
        # return [param for param in self.node.inst.parameters if self.isHwParam(param)]

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
        return isinstance(param.get_value(), int) or \
               (isinstance(param.param_type, ArrayPlaceholder) and param.param_type.element_type == int)

    def getSigVerilogName(self, s : Signal, intf : Intf | None = None) -> str:
        return self.node.inst_name + "_" + s.name

    def get_intfs(self):
        intfs_prop = self.node.get_property("intfs")
        if intfs_prop is None:
            return []
        intfs = []
        for p in intfs_prop:
            try:
                prefix = p.prefix
            except AttributeError:
                prefix = ""
            try:
                modport = list(IntfModport)[p.modport.value]
            except AttributeError:
                modport = IntfModport.SLAVE

            intf = create_intf(
                        self.rdlc,
                        parent_node=self.node,
                        intf_type=p.name,
                        addr_width=p.ADDR_WIDTH,
                        data_width=p.DATA_WIDTH,
                        prefix=prefix,
                        modport=modport,
                        )
            intfs.append(intf)

        return intfs
