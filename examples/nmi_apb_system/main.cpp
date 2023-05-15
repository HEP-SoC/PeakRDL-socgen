#include <cstdint>
#include <iostream>
#include <stdlib.h>
#include "Vnmi_system.h"
#include <vector>
#include <verilated.h>
#include <verilated_vcd_c.h>
#include <ctime>

#include "addrmap.h"

typedef Vnmi_system DUT;

uint32_t clk_cnt = 0;

void tick(DUT *dut, VerilatedVcdC *trace){
    clk_cnt++;
    dut->clk = 0;
    dut->eval();

    dut->clk = 0;
    dut->eval();
    trace->dump(10*clk_cnt+5);

    dut->clk = 1;
    dut->eval(); 
    trace->dump(10*clk_cnt+10);

}
void rst(DUT *dut, VerilatedVcdC *trace){
    for(int i = 0; i < 10; i++){
        tick(dut, trace);
    }
    dut->rstn = 1;

}

uint32_t random(uint32_t min, uint32_t max) //range : [min, max]
{
   return min + std::rand() % (( max + 1 ) - min);
}

uint32_t random(std::vector<uint32_t> &vec){
    uint32_t index = random(0, vec.size()-1);
    return vec[index];
}

void write32(DUT *dut, uint32_t addr, uint32_t data, VerilatedVcdC *trace){
    dut->s_nmi_addr = addr;
    dut->s_nmi_wdata = data;
    dut->s_nmi_wstrb = 0xff;
    dut->s_nmi_valid = 1;

    do{
        tick(dut, trace);
    }
    while(!(dut->s_nmi_valid && dut->s_nmi_ready));
        // tick(dut, trace);

    dut->s_nmi_valid = 0;
}

uint32_t read32(DUT *dut, uint32_t addr, VerilatedVcdC *trace){
    dut->s_nmi_addr = addr;
    dut->s_nmi_wstrb = 0x00;
    dut->s_nmi_valid = 1;
    
    do{
        tick(dut, trace);
    }
    while(!(dut->s_nmi_valid && dut->s_nmi_ready));

    dut->s_nmi_valid = 0;

    return dut->s_nmi_rdata;
}

void addrmap_rwv(DUT *dut, addrmap &a, VerilatedVcdC *trace){

    uint32_t wr_strb = random(0, 7);
    uint32_t wr_strb_ext = 0;

    for(int i = 0; i<3; i++)
        if(wr_strb & (0x1<<i))
            wr_strb_ext = wr_strb_ext | (0xFF << (i*8));

    uint32_t wr_data = random(0, 0x00FFFFFF) & wr_strb_ext;
    uint32_t wr_addr = random(a.base, a.base + (a.size - 4));

    write32(dut, wr_addr, wr_data, trace);
    uint32_t rd_data = read32(dut, wr_addr , trace);

    if(wr_data != (rd_data & 0x00FFFFFF)){
        a.print();
        std::cout << "Written to addr: 0x" << std::hex << wr_addr << "\n"
            << "    WR_Data: " << wr_data << "\n"
            << "    RD_data: " << (rd_data & 0x00FFFFFF) << "\n";
    }

}

int main(int argc, char **argv) {
	Verilated::commandArgs(argc, argv);
    Verilated::traceEverOn(true);
	DUT *top = new DUT;
    VerilatedVcdC	*m_trace;
    std::srand(std::time(nullptr));

    std::vector<addrmap> vec = get_addrmaps();

    for (auto &v : vec) {
        std::cout << "Path: " << v.path << " Addr; 0x" << std::hex << v.base << " ID: " << v.id << "\n";
    
    }


    m_trace = new VerilatedVcdC;
    top->trace(m_trace, 99);
    m_trace->open("trace.vcd");

	// Tick the clock until we are done
    top->rstn = 0;
    top->s_nmi_valid = 0;
	while(clk_cnt < 2000) {
        rst(top, m_trace);

        // if(top->s_nmi_valid && top->s_nmi_ready)
        
        addrmap_rwv(top, vec[random(0, vec.size()-1)], m_trace);
        // else
        //     valid_next = 0;
	} 
    m_trace->close();
    m_trace = NULL;
    delete top;
    top = NULL;

    return 0;
}
