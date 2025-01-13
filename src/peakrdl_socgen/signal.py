import re

from typing import TYPE_CHECKING
from systemrdl.node import SignalNode

if TYPE_CHECKING:
    from .intf import IntfPort

class Signal:
    """Wrapper around a SignalNode with extended properties for verilog module generation."""
    def __init__(self, node: SignalNode, prefix: str = "", cap: bool = False, regex: str = ""):

        self.node = node
        # Prefix appended to the signal name?
        self.prefix = prefix
        # Name of the node containing the signal
        self.basename = node.inst_name
        self.regex = regex

        self.width = node.width
        self.is_clk = self.isClk()
        self.is_rst = self.isRst()

        self.activelow = node.get_property('activelow', default=False) != False
        self.activehigh = node.get_property('activehigh', default=False) != False
        assert not (self.activelow and self.activehigh) == True, f"Signal cannot be both activelow and activehigh {self.name}"

        self.output = node.get_property('output', default=False) != False
        self.input = node.get_property('input', default=False) != False
        self.inout = node.get_property('inout', default=False) != False
        assert not (self.output and self.input) == True, f"Signal cannot be both input and output {self.name}"
        assert not (self.output and self.inout) == True, f"Signal cannot be both output and inout {self.name}"
        assert not (self.input and self.inout) == True, f"Signal cannot be both input and inout {self.name}"

        self.data_type = node.get_property('datatype', default='wire')

    @property
    def name(self):
        """Gets the signal instance name."""
        signal_base_name = self.prefix + self.node.inst_name

        # Apply regex if existing
        if self.regex:
            try:
                match_pattern, replace_pattern = self.regex.split('::', 1)
            except ValueError:
                raise ValueError("Invalid format for regex argument. Use 'match_pattern::replace_pattern'.")
            # Perform the regex replacement
            signal_base_name = re.sub(match_pattern, replace_pattern, signal_base_name)

        return signal_base_name

    @property
    def verilogDir(self):
        """Gets the signal direction in verilog format."""
        if self.input:
            return f"input  {self.data_type}"
        elif self.output:
            return f"output {self.data_type}"
        elif self.inout:
            return f"inout  {self.data_type}"
        elif self.is_clk or self.is_rst: # Is this really needed?
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
        return f"Signal: {self.name} Width: {self.width} Active low/high: {self.activelow}/{self.activehigh}"

class IntfSignal(Signal):
    """Extension of the base Signal class for interface signals."""
    def __init__(self, node: SignalNode, intf: 'IntfPort'):

        self.intf = intf
        # Call base class init method
        super().__init__(node=node, prefix=intf.prefix, cap=intf.cap, regex=intf.regex)
        # Get the signal interface specific properties
        self.ss =  node.get_property('ss', default=False)    != False
        self.miso = node.get_property('miso', default=False) != False
        self.mosi = node.get_property('mosi', default=False) != False
        assert (self.miso or self.mosi) == True, f"Intf Signal {self.name} does not have mosi or miso property"
        self.bidir = self.miso and self.mosi

    @property
    def name_port(self):
        """Gets the signal instance name for port definition with standard suffix added."""
        signal_base_name = self.prefix + self.node.inst_name

        # Add the _(n)i, _(n)o, or _(n)io suffix for interface ports
        # n for active low signals
        if self.activelow:
            signal_base_name += "_n"
        else:
            signal_base_name += "_"
        # i, o, io for input, output, and inout, respectively
        if self.bidir:
            signal_base_name += "io"
        elif self.mosi:
            if self.intf.modport.name == "slave":
                signal_base_name += "i"
            else:
                signal_base_name += "o"
        elif self.miso:
            if self.intf.modport.name == "master":
                signal_base_name += "i"
            else:
                signal_base_name += "o"
        else:
            assert False, "Intf Signal does not have mosi or miso property"

        # If it is a tmr signal it will have the format, e.g., paddrA_i
        # To create signal with same format than tmrg change it to, e.g., paddr_iA
        tmr_match_pattern = r"([ABC])_(n?[io])$"
        tmr_replace_pattern = r"_\2\1"
        signal_base_name = re.sub(tmr_match_pattern, tmr_replace_pattern, signal_base_name)

        # Apply regex if existing
        if self.regex:
            try:
                match_pattern, replace_pattern = self.regex.split('::', 1)
            except ValueError:
                raise ValueError(f"Invalid format for regex argument: {self.regex}. Use 'match_pattern::replace_pattern'.")
            # Perform the regex replacement
            signal_base_name = re.sub(match_pattern, replace_pattern, signal_base_name)

        # print(f'name_port - signal_base_name: {signal_base_name}')
        return signal_base_name

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
        return f"Signal: {self.name} Width: {self.width} SS: {self.ss} MOSI: {self.mosi} MISO: {self.miso} Active low/high: {self.activelow}/{self.activehigh}"
