module apb_interconnect #(
    parameter  N_SLAVES       = 3,
    parameter  N_MASTERS      = 1,
    parameter  APB_DATA_WIDTH = 32,
    parameter  APB_ADDR_WIDTH = 32,
    parameter [N_SLAVES*2*APB_ADDR_WIDTH-1:0] MEM_MAP = {32'h0000_0000, 32'h0000_1FFF, 32'h0000_2000, 32'h0000_3FFF, 32'h0000_4000, 32'h0000_9FFF},

    parameter  PSTRB_WIDTH = (APB_DATA_WIDTH-1)/8+1 // 4 bits for 32 data
)(
    // SLAVE PORT
    input   wire                        s_penable,
    input   wire                        s_pwrite,
    input   wire [APB_ADDR_WIDTH-1:0]   s_paddr,
    input   wire                        s_psel,
    input   wire [APB_DATA_WIDTH-1:0]   s_pwdata,
    input   wire [PSTRB_WIDTH-1:0]      s_pstrb,
    output  reg  [APB_DATA_WIDTH-1:0]   s_prdata,
    output  reg                         s_pready,
    output  reg                         s_pslverr,

    // MASTER PORTS
    output  reg                                  m_penable,
    output  reg                                  m_pwrite,
    output  reg  [APB_ADDR_WIDTH-1:0]            m_paddr,
    output  reg  [N_SLAVES-1:0]                  m_psel,
    output  reg  [APB_DATA_WIDTH-1:0]            m_pwdata,
    output  reg  [PSTRB_WIDTH-1:0]               m_pstrb,
    input   wire [APB_DATA_WIDTH*N_SLAVES-1:0]   m_prdata,
    input   wire [N_SLAVES-1:0]                  m_pready,
    input   wire [N_SLAVES-1:0]                  m_pslverr
);

    integer j;
    always @(*) begin : match_address
        m_psel   = {N_SLAVES{1'b0}};
        m_pwrite  = s_pwrite;
        m_paddr  = s_paddr;
        m_pwdata = s_pwdata;
        m_pstrb  = s_pstrb;

        // generate the select signal based on the supplied address
        for (j = 0; j < N_SLAVES; j++) begin
            m_psel[j]  =  s_psel && (s_paddr >= MEM_MAP[(N_SLAVES*2-2*j)  *APB_ADDR_WIDTH-1 -: APB_ADDR_WIDTH] &&
                                     s_paddr <= MEM_MAP[(N_SLAVES*2-1-2*j)*APB_ADDR_WIDTH-1 -: APB_ADDR_WIDTH]);
        end

    end

    wire [N_SLAVES-1:0] s_penable_exp;
    assign s_penable_exp = {N_SLAVES{s_penable_i}};
    // Assign other signals
    integer i;
    always @(*) begin
        // default assignment - keep silent by default
        s_prdata     = {APB_DATA_WIDTH{1'b0}};
        s_pready     = |(m_pready & m_psel);
        s_pslverr    = |(m_pslverr & m_psel);
        m_penable    = m_psel & s_penable_exp;
        // select the right master
        for (i = 0; i < N_SLAVES; i=i+1) begin
            if (m_psel[i]) begin
                // to peripherals
                // from peripherals
                s_prdata = m_prdata[i][APB_DATA_WIDTH-1:0];
            end
        end
    end
endmodule
