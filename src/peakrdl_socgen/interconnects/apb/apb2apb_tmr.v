module apb2apb_tmr #(
    parameter DATA_WIDTH = 32,
    parameter ADDR_WIDTH = 32,

    parameter WSTRB_WIDTH = (DATA_WIDTH-1)/8+1 // 4 bits for 32 data
)(
    input   wire clk,
    input   wire rstn,
    
    input wire                      s_penable,
    input wire                      s_pwrite,
    input wire                      s_psel,
    input wire [ADDR_WIDTH-1:0]     s_paddr,
    input wire [DATA_WIDTH-1:0]     s_pwdata,
    input wire [WSTRB_WIDTH-1:0]    s_pstrb,
    output wire [DATA_WIDTH-1:0]    s_prdata,
    output wire                     s_pready,
    output wire                     s_pslverr,

    // NMI triplicated output
    output  wire [2:0]               m_penable,
    output  wire [2:0]               m_pwrite,
    output  wire [2:0]               m_psel,
    output  wire [3*ADDR_WIDTH-1:0]  m_paddr,    
    output  wire [3*DATA_WIDTH-1:0]  m_pwdata,    
    output  wire [3*WSTRB_WIDTH-1:0] m_pstrb,    
    input   wire [3*DATA_WIDTH-1:0]  m_prdata,   
    input   wire [2:0]               m_pready,
    input   wire [2:0]               m_pslverr
);

    fanout                       penable_fanout (.in(s_penable), .out(m_penable));
    fanout                       pwrite_fanout (.in(s_pwrite), .out(m_pwrite));
    fanout                       psel_fanout (.in(s_psel), .out(m_psel));
    fanout #(.WIDTH(ADDR_WIDTH)) paddr_fanout  (.in(s_paddr), .out(m_paddr));
    fanout #(.WIDTH(DATA_WIDTH)) pwdata_fanout (.in(s_pwdata), .out(m_pwdata));
    fanout #(.WIDTH(WSTRB_WIDTH))pstrb_fanout (.in(s_pstrb), .out(m_pstrb));

    majorityVoter pready_voter (.in(m_pready), .out(s_pready)); 
    majorityVoter pslverr_voter (.in(m_pslverr), .out(s_pslverr)); 
    majorityVoter #(.WIDTH(DATA_WIDTH)) prdata_voter (.in(m_prdata), .out(s_prdata)); 

endmodule


