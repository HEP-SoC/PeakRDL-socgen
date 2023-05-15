module nmi2apb #(
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
	input   wire [DATA_WIDTH-1:0]    s_nmi_addr,
	input   wire [DATA_WIDTH-1:0]    s_nmi_wdata,
	input   wire [WSTRB_WIDTH-1:0]   s_nmi_wstrb,
	output  wire [DATA_WIDTH-1:0]    s_nmi_rdata,

    // APB master port
    output  wire                     m_psel,
    output  wire                     m_penable,
    output  wire                     m_pwrite,
    input   wire                     m_pready,
    output  wire [ADDR_WIDTH-1:0]    m_paddr,    
    output  wire [DATA_WIDTH-1:0]    m_pwdata,    
    output  wire [WSTRB_WIDTH-1:0]   m_pstrb,    
    input   wire [DATA_WIDTH-1:0]    m_prdata,   
    input   wire                     m_pslverr
);

    reg psel_del;

    // 1-cycle delay
    always @(posedge clk or negedge rstn) begin
        if (!rstn) psel_del <= 1'b0;
        else psel_del <= m_psel;
    end

    assign m_psel      = s_nmi_valid;
    assign m_penable   = m_psel & psel_del;
    assign s_nmi_ready = m_psel & m_penable & m_pready;

    // These are driven to 0 if PSEL is not active only as a recommandation, it's not really necessary
    assign m_pwrite    = m_psel ? |s_nmi_wstrb : 1'b0;
    assign m_paddr     = m_psel ? s_nmi_addr : {(ADDR_WIDTH){1'b0}};
    assign m_pstrb     = m_psel ? s_nmi_wstrb : {(WSTRB_WIDTH){1'b0}};
    assign m_pwdata    = m_psel ? s_nmi_wdata : {(DATA_WIDTH){1'b0}};
    assign s_nmi_rdata = m_psel ? m_prdata : {(DATA_WIDTH){1'b0}};
    
endmodule
