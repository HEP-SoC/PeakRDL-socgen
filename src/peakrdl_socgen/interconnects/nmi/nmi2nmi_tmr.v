module nmi2nmi_tmr #(
    parameter DATA_WIDTH = 32,
    parameter ADDR_WIDTH = 32,

    parameter WSTRB_WIDTH = (DATA_WIDTH-1)/8+1 // 4 bits for 32 data
)(
    input   wire clk,
    input   wire rstn,
    
    // PicoRV32 Native Memory Interface
    input   wire                     s_nmi_valid,
    input   wire                     s_nmi_instr,
	output  wire                     s_nmi_ready,
	input   wire [ADDR_WIDTH-1:0]    s_nmi_addr,
	input   wire [DATA_WIDTH-1:0]    s_nmi_wdata,
	input   wire [WSTRB_WIDTH-1:0]   s_nmi_wstrb,
	output  wire [DATA_WIDTH-1:0]    s_nmi_rdata,

    // NMI triplicated output
    output   wire [2:0]                 m_nmi_valid,
    output   wire [2:0]                 m_nmi_instr,
	input    wire [2:0]                 m_nmi_ready,
	output   wire [3*ADDR_WIDTH-1:0]    m_nmi_addr,
	output   wire [3*DATA_WIDTH-1:0]    m_nmi_wdata,
	output   wire [3*WSTRB_WIDTH-1:0]   m_nmi_wstrb,
	input    wire [3*DATA_WIDTH-1:0]    m_nmi_rdata
);

    fanout                       valid_fanout (.in(s_nmi_valid), .out(m_nmi_valid));
    fanout                       instr_fanout (.in(s_nmi_instr), .out(m_nmi_instr));
    fanout #(.WIDTH(ADDR_WIDTH)) addr_fanout  (.in(s_nmi_addr), .out(m_nmi_addr));
    fanout #(.WIDTH(DATA_WIDTH)) wdata_fanout (.in(s_nmi_wdata), .out(m_nmi_wdata));
    fanout #(.WIDTH(WSTRB_WIDTH))wstrb_fanout (.in(s_nmi_wstrb), .out(m_nmi_wstrb));

    majorityVoter ready_voter (.in(m_nmi_ready), .out(s_nmi_ready)); 
    majorityVoter #(.WIDTH(DATA_WIDTH)) rdata_voter (.in(m_nmi_rdata), .out(s_nmi_rdata)); 
endmodule

