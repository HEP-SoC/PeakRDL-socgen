module apb_interconnect #(
    parameter  N_MST_PORTS   = 3,
    parameter  DATA_WIDTH = 32,
    parameter  ADDR_WIDTH = 32,
    parameter [N_MST_PORTS*2*ADDR_WIDTH-1:0] MEM_MAP = {32'h0000_0000, 32'h0000_1FFF, 32'h0000_2000, 32'h0000_3FFF, 32'h0000_4000, 32'h0000_9FFF},

    parameter  PSTRB_WIDTH = (DATA_WIDTH-1)/8+1 // 4 bits for 32 data
)(
    // SLAVE PORT
    input   wire                        s_penable,
    input   wire                        s_pwrite,
    input   wire [ADDR_WIDTH-1:0]       s_paddr,
    input   wire                        s_psel,
    input   wire [DATA_WIDTH-1:0]       s_pwdata,
    input   wire [PSTRB_WIDTH-1:0]      s_pstrb,
    output  wire [DATA_WIDTH-1:0]       s_prdata,
    output  wire                        s_pready,
    output  wire                        s_pslverr,

    // MASTER PORTS
    output  wire                                 m_penable,
    output  wire                                 m_pwrite,
    output  wire [ADDR_WIDTH-1:0]                m_paddr,
    output  reg  [N_MST_PORTS-1:0]                  m_psel,
    output  wire [DATA_WIDTH-1:0]                m_pwdata,
    output  wire [PSTRB_WIDTH-1:0]               m_pstrb,
    input   wire [DATA_WIDTH*N_MST_PORTS-1:0]       m_prdata,
    input   wire [N_MST_PORTS-1:0]                  m_pready,
    input   wire [N_MST_PORTS-1:0]                  m_pslverr
);

    integer j;
    always @(*) begin : match_address
        m_psel   = {N_MST_PORTS{1'b0}};
        // generate the select signal based on the supplied address
        for (j = 0; j < N_MST_PORTS; j = j + 1) begin
            m_psel[j]  =  s_psel && (s_paddr >= MEM_MAP[(N_MST_PORTS*2-2*j)  *ADDR_WIDTH-1 -: ADDR_WIDTH] &&
                                     s_paddr <= MEM_MAP[(N_MST_PORTS*2-1-2*j)*ADDR_WIDTH-1 -: ADDR_WIDTH]);
        end
    end

    // Parametrizable N:1 mux
    muxNto1_onehot #(
        .WIDTH(DATA_WIDTH),
        .N(N_MST_PORTS)
    )   mux_prdata (
        .in(m_prdata),
        .out(s_prdata),
        .sel(m_psel)
    );

    assign s_pready =  |(m_pready & m_psel);
    assign s_pslverr = |(m_pslverr & m_psel);
    assign m_penable = s_penable;
    assign m_pwrite = s_pwrite;
    assign m_paddr = s_paddr;
    assign m_pwdata = s_pwdata;
    assign m_pstrb = s_pstrb;

endmodule

module muxNto1_onehot #(
    parameter WIDTH = 32,
    parameter N = 2
)
(
    input wire [WIDTH*N-1:0] in,
    output wire [WIDTH-1:0] out,
    input wire [N-1:0] sel
);
// Credit https://www.eevblog.com/forum/microcontrollers/simplify-verilog-code-(bus-mux)/
  /* verilator lint_off UNOPTFLAT */
   wire [N*WIDTH-1:0] repl;
   genvar i;
    generate 
        for (i = 0; i < N; i = i + 1) begin: data_mux
          if (0 == i)
            assign repl[0 +: WIDTH] = {(WIDTH){sel[i]}} & in[0 +: WIDTH];
          else
            assign repl[i*WIDTH +: WIDTH] = repl[(i-1) * WIDTH +: WIDTH] | {(WIDTH){sel[i]}} & in[i*WIDTH +: WIDTH];
        end
    endgenerate
  /* verilator lint_on UNOPTFLAT */
    assign out = repl[(N-1)*WIDTH +: WIDTH];


endmodule
