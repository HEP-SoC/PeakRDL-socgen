from typing import TYPE_CHECKING
from systemrdl.node import SignalNode

if TYPE_CHECKING:
    from .intf import IntfPort

class Signal:
    """Wrapper around a SignalNode with extended properties for verilog module generation."""
    def __init__(self, node: SignalNode, prefix: str = "", cap: bool = False):

        self.node = node
        # Prefix appended to the signal name?
        self.prefix = prefix
        # Name of the node containing the signal
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
        """Gets the signal instance name."""
        if self.cap:
            return self.prefix + self.node.inst_name.upper()
        return self.prefix + self.node.inst_name

    @property
    def verilogDir(self):
        """Gets the signal direction in verilog format."""
        if self.input:
            return f"input  {self.data_type}"
        elif self.output:
            return f"output {self.data_type}"
        elif self.is_clk or self.is_rst:
            return f"input  {self.data_type}"

        assert False, f"Signal does not have input or output"

    def isClk(self):
        """Returns True if signal type is defined as clk."""
        if self.node.get_property("clock") is not None:
            return True
        else:
            return False

    def isRst(self):
        """Returns True if signal type is defined as rst."""
        if self.node.get_property("reset_signal") is not None:
            return True
        else:
            return False

    def print(self):
        """Prints the signal properties."""
        print(self.__str__)

    def __str__(self) -> str:
        return f"Signal: {self.name} Width: {self.width} Cap: {self.cap} Active low/high: {self.activelow}/{self.activehigh}"

class IntfSignal(Signal):
    """Extension of the base Signal class for interface signals."""
    def __init__(self, node: SignalNode, intf: 'IntfPort'):

        self.intf = intf
        # Sse base class init method
        super().__init__(node=node, prefix=intf.prefix, cap=intf.cap)
        # Get the signal interface specific properties
        self.ss =  node.get_property('ss', default=False)    != False
        self.miso = node.get_property('miso', default=False) != False
        self.mosi = node.get_property('mosi', default=False) != False
        self.bidir = self.miso and self.mosi

    @property
    def verilogDir(self):
        """Gets the signal interface direction in verilog format."""
        if self.miso ^ (self.intf.modport.name == "slave"):
            return "input  wire"
        elif self.mosi ^ (self.intf.modport.name == "slave"):
            return "output wire"

        assert False, "Intf Signal does not have mosi or miso property"

    def isShared(self):
        """Returns True if signal is shared (e.g., an address provided to slaves?)."""
        return not self.ss and not self.miso  # TODO what happens for bidir?

    def isOnlyMiso(self):
        """Returns True if signal is miso only."""
        return self.miso and not self.mosi

    def isOnlyMosi(self):
        """Returns True if signal is mosi only."""
        return self.mosi and not self.miso

    def __str__(self) -> str:
        return f"Signal: {self.name} Width: {self.width} SS: {self.ss} MOSI: {self.mosi} MISO: {self.miso} Cap: {self.cap} Active low/high: {self.activelow}/{self.activehigh}"
