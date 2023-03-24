
module nmi_interconnect #(
    parameter ADDR_WIDTH = 32,
    parameter DATA_WIDTH = 32,

    parameter N_SLAVES  = 3,
    parameter N_MASTERS  = 1,

    parameter [N_SLAVES*2*ADDR_WIDTH-1:0] MEM_MAP = {32'h1111_0000, 32'h1111_1FFF, 32'h2222_1000, 32'h2222_9FFF, 32'h3433_3000, 32'h3343_9FFF},

    parameter WSTRB_WIDTH = (DATA_WIDTH-1)/8+1 // 4 bits for 32 data

    )(
    input      s_nmi_valid,
    input      s_nmi_instr,
    output reg s_nmi_ready,

    input      [ADDR_WIDTH-1:0]  s_nmi_addr,
    input      [DATA_WIDTH-1:0]  s_nmi_wdata,
    input      [WSTRB_WIDTH-1:0] s_nmi_wstrb,
    output reg     [DATA_WIDTH-1:0]  s_nmi_rdata,

    output reg  [N_SLAVES-1:0] m_nmi_valid,
    output      [N_SLAVES-1:0] m_nmi_instr,
    input       [N_SLAVES-1:0] m_nmi_ready,

    output      [N_SLAVES*ADDR_WIDTH-1:0]  m_nmi_addr,
    output      [N_SLAVES*DATA_WIDTH-1:0]  m_nmi_wdata,
    output      [N_SLAVES*WSTRB_WIDTH-1:0] m_nmi_wstrb,
    input       [N_SLAVES*DATA_WIDTH-1:0]  m_nmi_rdata

    
    );

    genvar j;
    generate
        for(j=0; j<N_SLAVES; j=j+1) begin
           assign m_nmi_instr[j] = s_nmi_instr;
           assign m_nmi_addr[(j+1)*ADDR_WIDTH-1:j*ADDR_WIDTH] = s_nmi_addr;
           assign m_nmi_wdata[(j+1)*DATA_WIDTH-1:j*DATA_WIDTH] = s_nmi_wdata;
           assign m_nmi_wstrb[(j+1)*WSTRB_WIDTH-1:j*WSTRB_WIDTH] = s_nmi_wstrb;
        end
    endgenerate
    
    integer i;
    always @(*) begin
        s_nmi_rdata = {(DATA_WIDTH){1'b0}};
        s_nmi_ready = 1'b1;
        s_nmi_rdata = {(DATA_WIDTH/16){16'hC0DE}};
        for(i=0; i<N_SLAVES; i=i+1) begin
            m_nmi_valid[i] = 1'b0;
            if ( s_nmi_addr >= MEM_MAP[(N_SLAVES*2-2*i)  *ADDR_WIDTH-1 -: ADDR_WIDTH] &&
                    s_nmi_addr <= MEM_MAP[(N_SLAVES*2-1-2*i)*ADDR_WIDTH-1 -: ADDR_WIDTH]) begin
                    s_nmi_rdata = m_nmi_rdata[(i+1)*DATA_WIDTH-1 -: DATA_WIDTH];
                    m_nmi_valid[i] = s_nmi_valid;
                    s_nmi_ready = m_nmi_ready[i];
                end
        end
    end
     
endmodule
