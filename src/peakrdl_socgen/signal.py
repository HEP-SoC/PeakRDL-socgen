from enum import Enum
from systemrdl.node import SignalNode

class SignalType(Enum):  # TODO make it same type as the RDL one
    OUTPUT = 0
    INPUT  = 1
    BIDIRECTIONAL = 2
    TRISTATE = 3
    CLK = 4
    RST = 5
    WIRE = 6
    BLANK = 7


class Signal:
    def __init__(self,
            node : SignalNode,
            prefix : str = "",
            cap : bool = False,
            ):

        self.node = node

        # self.sig_name = prefix + node.inst_name # TOOD check if correct
        self.prefix = prefix
        self.basename = node.inst_name
        self.cap = cap

        self.width = node.width
        self.is_clk = self.isClk()
        self.is_rst = self.isRst()
        
        self.activelow = node.get_property('activelow', default=False) != False
        self.activehigh = node.get_property('activehigh', default=False) != False

        self.output = node.get_property('output', default=False) != False
        self.input = node.get_property('input', default=False) != False
        assert not (self.output==True and self.input) == True, f"Signal cannot be both input and output {self.name}"
        
        self.data_type = node.get_property('datatype', default='wire')

    @property
    def name(self):
        if self.cap:
            return self.prefix + self.node.inst_name.upper()
        return self.prefix + self.node.inst_name

    @property
    def verilogDir(self):
        if self.input:
            return f"input {self.data_type}"
        elif self.output:
            return f"output {self.data_type}"
        elif self.is_clk or self.is_rst:
            return f"input {self.data_type}"

        assert False, f"Signal does not have input or output"

    def isShared(self):
        return not self.ss and not self.miso  # TODO what happens for bidir?

    def isOnlyMiso(self):
        return self.miso and not self.mosi

    def isOnlyMosi(self):
        return self.mosi and not self.miso

    def isClk(self):
        typ = self.node.get_property("signal_type", default=False)
        if typ == False:
            return False
        if typ.name == 'clk':
            return True
        return False

    def isRst(self):
        typ = self.node.get_property("signal_type", default=False)
        if typ == False:
            return False
        if typ.name == 'rst':
            return True
        return False

    def print(self):
        print("Signal: ", self.name, " Width: ", self.width, " Cap: ", self.cap, " Active low/high", self.activelow, self.activehigh)

    def __str__(self) -> str:
        return f"Signal: {self.name} Width: {self.width} Cap: {self.cap} Active low/high: {self.activelow} {self.activehigh}"

class IntfSignal(Signal):

    def __init__(self,
            node : SignalNode,
                 intf : "Intf", # type: ignore
            ):

        self.intf = intf

        super().__init__(
                node=node,
                prefix=intf.prefix,
                cap=intf.cap,
                )

        self.ss =  node.get_property('ss', default=False)    != False
        self.miso = node.get_property('miso', default=False) != False
        self.mosi = node.get_property('mosi', default=False) != False
        self.bidir = self.miso and self.mosi

    def print(self):
        print("Signal: ", self.name, " Width: ", self.width, " SS: ", self.ss, " MOSI: ", self.mosi, " MISO ", self.miso, " Cap: ", self.cap, " Active low/high", self.activelow, self.activehigh)

    @property
    def verilogDir(self):
        if self.miso ^ (self.intf.modport.name == "slave"):
            return "input wire "
        elif self.mosi ^ (self.intf.modport.name == "slave"):
            return "output wire "

        assert False, f"Intf Signal does not have mosi or miso property"
