module apb_memory #(
    parameter ADDR_WIDTH = 32,
    parameter DATA_WIDTH = 32,
    parameter MEM_SIZE = 32,
    parameter ID = 0,

    parameter WSTRB_WIDTH = (DATA_WIDTH-1)/8+1 // 4 bits for 32 data
    
    ) (
    input clk,
    input rstn,

    input wire s_penable,
    input wire s_pwrite,
    input wire s_psel,
    input wire [ADDR_WIDTH-1:0]  s_paddr,
    input wire [DATA_WIDTH-1:0]  s_pwdata,
    input wire [WSTRB_WIDTH-1:0] s_pstrb,
    output      [DATA_WIDTH-1:0] s_prdata,
    output reg                   s_pready,
    output reg                   s_pslverr
    );



    reg [DATA_WIDTH-1:0] mem [0:MEM_SIZE/4-1];
    wire [DATA_WIDTH-1:0] wr_mask;
    genvar i;
    generate
    for (i = 0; i < WSTRB_WIDTH; i=i+1) begin
        assign wr_mask[i*8 +: 8] = {8{s_pstrb[i]}};
    end
    endgenerate

    assign s_prdata = (mem[s_paddr>>2] & 32'h00FFFFFF) | (ID << 24); // Append ID up for recognition


    always @(posedge clk) begin
        s_pready = 1'b0;
        if(s_penable)
            s_pready = 1'b1;
        if(s_penable && s_psel) begin

            if(s_pstrb > 0) begin
                mem[s_paddr>>2] <= (mem[s_paddr>>2] & ~wr_mask) | (s_pwdata & wr_mask);
            end
        end
    end

endmodule

