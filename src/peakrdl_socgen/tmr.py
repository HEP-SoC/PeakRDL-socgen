# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2025 CERN
#
# Please retain this header in all redistributions and modifications of the code.

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import logging

from systemrdl import RDLCompiler
from systemrdl.component import Addrmap, Signal as SignalComponent
from systemrdl.node import AddrmapNode
from systemrdl.rdltypes.user_struct import UserStruct
from systemrdl.udp import UDPDefinition

from .intf import IntfPort

# Logger generation for tmr module
tmr_logger = logging.getLogger("tmr_logger")
# Console handler
ch = logging.StreamHandler()
# create formatter and add it to the handlers
formatter = logging.Formatter('%(name)s - %(levelname)s: %(message)s')
ch.setFormatter(formatter)
# add the handlers to the logger
tmr_logger.addHandler(ch)
# Set for more verbosity
tmr_logger.setLevel(logging.INFO)

# Suffixes appended to each copy of a triplicated signal (TMRG convention)
TMR_COPIES = ("A", "B", "C")


class TmrUdp(UDPDefinition):
    """Set to false on a signal or an addrmap instance to keep it non-triplicated in TMR mode."""
    name = "tmr"
    valid_components = {SignalComponent, Addrmap}
    valid_type = bool


class TmrTypeUdp(UDPDefinition):
    """Overrides the TMR type name of an addrmap instance (default: <type_name><suffix>)."""
    name = "tmr_type"
    valid_components = {Addrmap}
    valid_type = str


class TmrIntfUdp(UDPDefinition):
    """Set on a <type>_intf_node to name the struct of its TMR counterpart interface."""
    name = "tmr_intf"
    valid_components = {Addrmap}
    valid_type = str


TMR_UDPS = [TmrUdp, TmrTypeUdp, TmrIntfUdp]

# Interface struct whose members (modport, prefix, cap, regex) name the ports of a module, the members added by
# the derived interface structs (e.g., SECDED_DATA, DATA_WIDTH) are the protocol parameters
NAMING_INTF_STRUCT = "base_intf"


def register_tmr_udps(rdlc: RDLCompiler) -> None:
    """Registers the TMR properties as soft UDPs (active only if declared in the RDL sources)."""
    for udp in TMR_UDPS:
        rdlc.register_udp(udp)


@dataclass
class TmrConfig:
    """Options of the TMR mode passed from the command line to the exporter."""
    # Compiler holding every input file, i.e., the non-TMR and the TMR definitions
    design_rdlc: RDLCompiler
    # Suffix appended to the non-TMR type names
    suffix: str = "TMR"
    # User mapping from non-TMR to TMR interface struct names (overrides the tmr_intf property)
    intf_map: Dict[str, str] = field(default_factory=dict)


class TmrContext:
    """Derives the TMR view of a design described once, without TMR, in SystemRDL.

    - Leaf modules are replaced by their TMR definition (<type_name><suffix> or tmr_type)
      elaborated with the same parameters. Their interfaces take the protocol members (e.g., SECDED_DATA)
      of the parent subsystem interface of the same TMR type, if any.
    - Subsystem signals are triplicated (A, B, C) unless 'tmr = false' is set.
    - Subsystem interfaces are mapped to their TMR counterpart declared with the 'tmr_intf'
      property of the interface node (e.g., obi_intf -> obiTMR_intf).
    """
    def __init__(self, config: TmrConfig, glue_rdlc: RDLCompiler):
        self.design_rdlc = config.design_rdlc
        self.suffix = config.suffix
        self.glue_rdlc = glue_rdlc

        # Non-TMR to TMR interface struct names, e.g., {'obi_intf': 'obiTMR_intf'}
        self.intf_map = self._getIntfMap(config.intf_map)
        # TMR to non-TMR interface struct names, an interface kept as is in TMR (e.g., apb_rt_intf) is the
        # non-TMR one only if no other interface is mapped to it (e.g., apb_intf -> apb_rt_intf)
        self.base_intf_map: Dict[str, str] = {}
        for base, tmr in self.intf_map.items():
            if self.base_intf_map.get(tmr, tmr) == tmr:
                self.base_intf_map[tmr] = base

        self._default_node_cache: Dict[str, AddrmapNode] = {}

    def _getIntfMap(self, user_map: Dict[str, str]) -> Dict[str, str]:
        """Returns the interface mapping declared on the interface nodes and overridden by the user one."""
        intf_map = {}
        for name in self.glue_rdlc.root.comp_defs:
            if not name.endswith("_intf_node"):
                continue
            node = self.glue_rdlc.elaborate(top_def_name=name, inst_name=name).get_child_by_name(name)
            tmr_intf = node.get_property("tmr_intf", default=None)
            if tmr_intf:
                intf_map[name.replace("_node", "")] = tmr_intf
        intf_map.update(user_map)
        tmr_logger.info(f"TMR interface mapping: {intf_map}")
        return intf_map

    @staticmethod
    def isTmr(node) -> bool:
        """Returns False if the node is explicitly excluded from triplication."""
        return node.get_property("tmr", default=True) is not False

    def getTypeName(self, node: AddrmapNode) -> str:
        """Returns the TMR type name of an addrmap node."""
        tmr_type = node.get_property("tmr_type", default=None)
        if tmr_type:
            return tmr_type
        base_name = node.orig_type_name if node.orig_type_name is not None else node.inst_name
        return base_name + self.suffix

    def getBaseIntfNodeType(self, intf_node_type: str) -> str:
        """Returns the non-TMR interface node type of an interface node type (e.g., obiTMR_intf_node -> obi_intf_node)."""
        intf_type = intf_node_type.replace("_node", "")
        return self.base_intf_map.get(intf_type, intf_type) + "_node"

    def _getDefaultNode(self, type_name: str) -> AddrmapNode:
        """Returns a component definition elaborated with its default parameters."""
        if type_name not in self._default_node_cache:
            if type_name not in self.design_rdlc.root.comp_defs:
                raise ValueError(f"TMR definition '{type_name}' not found, make sure the TMR IP SystemRDL files are listed.")
            node = self.design_rdlc.elaborate(top_def_name=type_name, inst_name=type_name).get_child_by_name(type_name)
            self._default_node_cache[type_name] = node
        return self._default_node_cache[type_name]

    @staticmethod
    def getProtocolMembers(intf_struct: UserStruct) -> List[str]:
        """Returns the protocol members of an interface struct, i.e., the ones not naming the module ports."""
        naming_members = set()
        for cls in type(intf_struct).__mro__:
            if cls.__name__ == NAMING_INTF_STRUCT:
                naming_members = set(cls._members.keys())
                break
        return [k for k in intf_struct._members.keys() if k not in naming_members]

    def _getParentIntfParams(self, base_node: AddrmapNode, type_name: str) -> Dict[str, UserStruct]:
        """Returns the interface parameters of a TMR definition matching the TMR interface of the parent subsystem.

        The TMR leaf modules are connected to the parent interconnect without adapters, so the protocol members of
        their interface (e.g., SECDED_DATA, DATA_WIDTH) are the ones of the parent interface of the same TMR type.
        The naming members (modport, prefix, ...) describe the TMR module ports and keep their default value.
        """
        parent_intfs: Dict[str, List[UserStruct]] = {}
        for intf_struct in base_node.parent.get_property("ifports", default=[]):
            tmr_struct = self.getIntfStruct(intf_struct)
            parent_intfs.setdefault(tmr_struct.__class__.__name__, []).append(tmr_struct)

        params = {}
        for p in self._getDefaultNode(type_name).inst.parameters:
            default = p.get_value()
            if not isinstance(default, UserStruct):
                continue
            struct_type = default.__class__.__name__
            matches = parent_intfs.get(struct_type, [])
            if not matches:
                continue
            if len(matches) > 1:
                raise ValueError(f"Parameter {p.name} of {type_name} ({base_node.get_path()}) matches several "
                                 f"{struct_type} interfaces of {base_node.parent.get_path()}, cannot select one.")
            protocol_members = self.getProtocolMembers(default)
            parent_values = matches[0]._values
            intf_dict = {k: parent_values[k] if k in protocol_members else v for k, v in default._values.items()}
            # Built directly (not evaluated from a string) to keep the escaped string members (e.g., regex) as is
            params[p.name] = type(default)(intf_dict)
        return params

    def getLeafNode(self, base_node: AddrmapNode) -> AddrmapNode:
        """Returns the TMR definition of a leaf module elaborated with the parameters of its non-TMR instance."""
        type_name = self.getTypeName(base_node)
        tmr_param_names = [p.name for p in self._getDefaultNode(type_name).inst.parameters]

        params = {}
        for p in base_node.inst.parameters:
            value = p.get_value()
            # The TMR definition keeps its own interface (e.g., apb_rt_intf instead of apb_intf)
            if isinstance(value, UserStruct) or (isinstance(value, list) and value and isinstance(value[0], UserStruct)):
                continue
            if p.name in tmr_param_names:
                params[p.name] = value
            else:
                tmr_logger.debug(f"Parameter {p.name} of {base_node.get_path()} does not exist in {type_name}, skipped.")

        # Except for the protocol members of the interfaces matching the parent subsystem ones
        params.update(self._getParentIntfParams(base_node, type_name))

        root = self.design_rdlc.elaborate(top_def_name=type_name, inst_name=base_node.inst_name, parameters=params)
        return root.get_child_by_name(base_node.inst_name)

    def getIntfStruct(self, intf_struct: UserStruct) -> UserStruct:
        """Returns the TMR counterpart of a non-TMR interface struct value.

        Members with the same name are copied, members only existing in the TMR struct get the default
        value of the TMR interface node, and members only existing in the non-TMR struct are dropped.
        """
        base_type = intf_struct.__class__.__name__
        # Interconnect port structs (e.g., obi_intc) extend the interface ones (e.g., obi_intf)
        is_intc = base_type.endswith("_intc")
        base_intf = base_type.replace("_intc", "_intf") if is_intc else base_type
        if base_intf not in self.intf_map:
            raise ValueError(f"No TMR interface declared for {base_intf}, set 'tmr_intf' on {base_intf}_node or use --intf-map.")
        tmr_intf = self.intf_map[base_intf]

        # Default member values of the TMR interface struct
        tmr_node_name = tmr_intf + "_node"
        tmr_node = self.glue_rdlc.elaborate(top_def_name=tmr_node_name, inst_name=tmr_node_name).get_child_by_name(tmr_node_name)
        tmr_defaults = tmr_node.get_property("intf_inst")._values

        values = {k: intf_struct._values.get(k, v) for k, v in tmr_defaults.items()}
        tmr_type = tmr_intf
        if is_intc:
            values['N_PORTS'] = intf_struct._values['N_PORTS']
            tmr_type = tmr_intf.replace("_intf", "_intc")

        return self.glue_rdlc.eval(IntfPort.get_intf_param_string(intf_type=tmr_type, intf_dict=values))
