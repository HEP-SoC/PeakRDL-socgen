module nmi_tmr2nmi #(
    parameter DATA_WIDTH = 32,
    parameter ADDR_WIDTH = 32,

    parameter WSTRB_WIDTH = (DATA_WIDTH-1)/8+1 // 4 bits for 32 data
)(
    input   wire clk,
    input   wire rstn,
    
    // NMI triplicated input 
    input   wire [2:0]                 s_nmi_valid,
    input   wire [2:0]                 s_nmi_instr,
	output  wire [2:0]                 s_nmi_ready,
	input   wire [3*ADDR_WIDTH-1:0]    s_nmi_addr,
	input   wire [3*DATA_WIDTH-1:0]    s_nmi_wdata,
	input   wire [3*WSTRB_WIDTH-1:0]   s_nmi_wstrb,
	output  wire [3*DATA_WIDTH-1:0]    s_nmi_rdata,

    // NMI  voted output
    output   wire                       m_nmi_valid,
    output   wire                       m_nmi_instr,
	input    wire                       m_nmi_ready,
	output   wire [ADDR_WIDTH-1:0]      m_nmi_addr,
	output   wire [DATA_WIDTH-1:0]      m_nmi_wdata,
	output   wire [WSTRB_WIDTH-1:0]     m_nmi_wstrb,
	input    wire [DATA_WIDTH-1:0]      m_nmi_rdata
);

    fanout                       ready_fanout (.in(m_nmi_ready), .out(s_nmi_ready));
    fanout #(.WIDTH(DATA_WIDTH)) rdata_fanout (.in(m_nmi_rdata), .out(s_nmi_rdata));

    majorityVoter                       valid_voter (.in(s_nmi_valid), .out(m_nmi_valid)); 
    majorityVoter                       instr_voter (.in(s_nmi_instr), .out(m_nmi_instr)); 
    majorityVoter #(.WIDTH(DATA_WIDTH)) wdata_voter (.in(s_nmi_wdata), .out(m_nmi_wdata)); 
    majorityVoter #(.WIDTH(ADDR_WIDTH)) addr_voter (.in(s_nmi_addr), .out(m_nmi_addr)); 
    majorityVoter #(.WIDTH(WSTRB_WIDTH))wstrb_voter (.in(s_nmi_wstrb), .out(m_nmi_wstrb)); 
endmodule


