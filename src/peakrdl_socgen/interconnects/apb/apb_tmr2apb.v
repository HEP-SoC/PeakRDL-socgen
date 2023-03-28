module apb_tmr2apb #(
    parameter DATA_WIDTH = 32,
    parameter ADDR_WIDTH = 32,

    parameter WSTRB_WIDTH = (DATA_WIDTH-1)/8+1 // 4 bits for 32 data
)(
    input   wire clk,
    input   wire rstn,
    
    input wire [2:0]                  s_penable,
    input wire [2:0]                  s_pwrite,
    input wire [2:0]                  s_psel,
    input wire [3*ADDR_WIDTH-1:0]     s_paddr,
    input wire [3*DATA_WIDTH-1:0]     s_pwdata,
    input wire [3*WSTRB_WIDTH-1:0]    s_pstrb,
    output wire [3*DATA_WIDTH-1:0]    s_prdata,
    output wire [2:0]                 s_pready,
    output wire [2:0]                 s_pslverr,

    output  wire                     m_penable,
    output  wire                     m_pwrite,
    output  wire                     m_psel,
    output  wire [ADDR_WIDTH-1:0]    m_paddr,    
    output  wire [DATA_WIDTH-1:0]    m_pwdata,    
    output  wire [WSTRB_WIDTH-1:0]   m_pstrb,    
    input   wire [DATA_WIDTH-1:0]    m_prdata,   
    input   wire                     m_pready,
    input   wire                     m_pslverr
);

    fanout                       pslverr_fanout (.in(s_pslverr), .out(m_pslverr));
    fanout                       pready_fanout (.in(s_pready), .out(m_pready));
    fanout #(.WIDTH(DATA_WIDTH)) prdata_fanout (.in(s_prdata), .out(m_prdata));

    majorityVoter #(.WIDTH(WSTRB_WIDTH)) pstrb_voter (.in(m_pstrb), .out(s_pstrb)); 
    majorityVoter #(.WIDTH(DATA_WIDTH))  pwdata_voter (.in(m_pwdata), .out(s_pwdata)); 
    majorityVoter #(.WIDTH(ADDR_WIDTH))  paddr_voter (.in(m_paddr), .out(s_paddr)); 
    majorityVoter                        psel_voter (.in(m_psel), .out(s_psel)); 
    majorityVoter                        pwrite_voter (.in(m_pwrite), .out(s_pwrite)); 
    majorityVoter                        penable_voter (.in(m_penable), .out(s_penable)); 

endmodule



