from typing import Tuple
from systemrdl import RDLCompiler
from systemrdl.node import AddrmapNode
from .module import Module
from .intf import Intf, IntfModport, Signal
from .intc import IntcBase

 
class Adapter(Module):
    def __init__(self, 
            adapt_from : Intf,
            adapt_to : Intf,
            rdlc : RDLCompiler,
            ):
        self.adapt_from = adapt_from
        self.adapt_to = adapt_to
        self.ext_ports = [adapt_from, adapt_to]

        # print("----- ADAPT FROM")
        # adapt_from.print()
        # print("----- ADAPT TO")
        # adapt_to.print()
        self.rdlc = rdlc

        self.node = self.create_adapter_node()


        super().__init__(self.node, self.rdlc) # type: ignore

        # self.assignOriginalIntfs()

        # for intf in self.intfs:
        #     intf.print()

    def adapterDrivesExtPort(self):
        return self.ext_port.modport == IntfModport.MASTER

    def getLeftIntf(self):
        if self.adapt_from.modport == IntfModport.MASTER:
            return self.getSlaveIntfs()[0]

    def getRightIntf(self):
        if self.adapt_to.modport == IntfModport.MASTER:
            return self.getMasterIntfs()[0]


    @property
    def otherExtPort(self):
        if self.adapterDrivesExtPort():
            return self.getSlaveIntfs()[0]
        else:
            return self.getMasterIntfs()[0]

    def isDriver(self, s : Signal, intf : Intf):
        if intf not in [self.ext_port]:
            assert False, f"Interface is not connected to interconnect {intf.parent_node.inst_name}_{intf.sig_prefix}{intf.name}"

        if self.adapterDrivesExtPort():
            if s.isOnlyMiso():
                return True
            elif s.isOnlyMosi():
                return False
        else:
            if s.isOnlyMiso():
                return False
            elif s.isOnlyMosi():
                return True

        assert False, f"Interface is not connected to interconnect {intf.parent_node.inst_name}_{intf.sig_prefix}{intf.name}"


    def get_intfs(self):
        intfs = []
        for a in self.getAddrmaps():
            if a.get_property("intf"):
                intfs.append(self.construcIntf(a)) # type: ignore

        return intfs

    def construcIntf(self,
            intf : AddrmapNode,
            ):
        intf_inst = intf.get_property("intf_inst").members
        n_array = intf.get_property("n_array")
        try:
            cap = intf_inst['cap']
        except:
            cap = False

        return Intf(
                intf, 
                self.node, # type: ignore 
                self.rdlc,
                sig_prefix=intf_inst['prefix'],
                modport=list(IntfModport)[intf_inst['modport'].value],
                N=n_array,
                capitalize=cap,
                )

    def create_adapter_node(self):
        adapter_name = self.adapt_from.name.replace("_intf", "") + "2" + self.adapt_to.name.replace("_intf", "")
        inst_name = adapter_name + str(self.__hash__())[-3:]
        adapter = self.rdlc.elaborate(
                top_def_name=adapter_name,
                inst_name=inst_name,
                ).get_child_by_name(inst_name)

        return adapter

    # def assignOriginalIntfs(self): # TODO merge with intc_wrapper
    #     print("------------------- Assigning original interface for ", self.node.inst_name)
    #     self.ext_ports[0].print()
    #     print(self.ext_ports[0].parent_node.inst_name)
    #     self.ext_ports[0].orig_intf.print()
        # for intf in self.intfs:
        #     intf.print()
        #     for orig in [*self.ext_ports]:
        #         print("==========")
        #         print(orig.orig_intf.parent_node.inst_name + "_" + orig.orig_intf.sig_prefix)
        #         print(intf.orig_intf.sig_prefix)
        #         if orig.parent_node.inst_name + "_" + orig.sig_prefix == intf.orig_intf.sig_prefix:
        #             print("FOUND")
        #             intf.orig_intf = orig
    
    # def findFittingAdapter(self, intf : Intf, intc : "IntcBase"):
    #     available_adapters = ["axi2axi_lite", "axi_lite2apb", "nmi2apb"] # TODO find it automatically
    #
    #     if intf.name == intc.intf_type_name:
    #         return None
    #     adapter_name = None
    #     if intf.modport == IntfModport.MASTER:
    #         adapter_name = intc.intf_type_name.replace("_intf", "") + "2" + intf.name.replace("_intf", "")
    #     elif intf.modport == IntfModport.SLAVE:
    #         adapter_name = intf.name.replace("_intf", "") + "2" + intc.intf_type_name.replace("_intf", "")
    #
    #     if adapter_name not in available_adapters:
    #         print("Could not find, try to combine", adapter_name)
    #         fitting_slaves = []
    #         fitting_masters = []
    #         for a in available_adapters:
    #             if a.split("2")[0] == adapter_name.split("2")[0]: # type: ignore
    #                 fitting_slaves.append(a)
    #
    #             if a.split("2")[1] == adapter_name.split("2")[1]: # type: ignore
    #                 fitting_masters.append(a)
    #         
    #         fitting_adapters = []
    #         for slv in fitting_slaves:
    #             for mst in fitting_masters:
    #                 if slv.split("2")[1] == mst.split("2")[0]:
    #                     fitting_adapters.append([slv, mst])
    #                 
    #
    #         print("fitting slaves: ", fitting_slaves)
    #         print("fitting masters: ", fitting_masters)
    #         print("fitting adapters: ", fitting_adapters)
    #     print(adapter_name)
    #
    #     # print(self.intc_base.)
    #     # intf_types = ["axi_intf", "apb_intf", "axi_lite_intf", "nmi_intf"]
    #     # available_adapters = []
    #     # print("Ignore fatal errors in this function")
    #     # for comb in itertools.combinations(intf_types, 2):
    #     #     for cmb in [comb, comb[::-1]]: # Normal and reversed
    #     #         adapter_type = cmb[0].replace("_intf", "") + "2" + cmb[1].replace("_intf", "")
    #     #         adapter = None
    #     #         try:
    #     #             print(adapter_type)
    #     #             adapter = self.rdlc.elaborate(
    #     #                     top_def_name=adapter_type
    #     #                     )
    #     #         except:
    #     #             pass
    #     #         if adapter is not None:
    #     #             available_adapters.append(adapter_type)
    #     #
    #     # print(available_adapters)
    #     #
    #     #
    #     #
    #     pass
    #
    #
