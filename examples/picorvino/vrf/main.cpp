#include <cstdint>
#include <iostream>
#include <stdlib.h>
#include "Vpicorvino_wrap.h"
#include <vector>
#include <verilated.h>
#include <verilated_vcd_c.h>

typedef Vpicorvino_wrap DUT;

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

int main(int argc, char **argv) {
	Verilated::commandArgs(argc, argv);
    Verilated::traceEverOn(true);
	DUT *top = new DUT;
    VerilatedVcdC	*m_trace;

    m_trace = new VerilatedVcdC;
    top->trace(m_trace, 99);
    m_trace->open("trace.vcd");

	// Tick the clock until we are done
    top->rstn = 0;
    rst(top, m_trace);
	while(clk_cnt < 2000) {
        tick(top, m_trace);


	} 
    m_trace->close();
    m_trace = NULL;
    delete top;
    top = NULL;

    return 0;
}

