module nmi_memory #(
        parameter ADDR_WIDTH = 32,
        parameter DATA_WIDTH = 32,
        parameter MEM_SIZE = 2048,


        parameter WSTRB_WIDTH = (DATA_WIDTH-1)/8+1 // 4 bits for 32 data
    )(
    input  clk,
    input  rstn,

    input  s_mem_valid,
    input  s_mem_instr,
    output s_mem_ready,

    input      [ADDR_WIDTH-1:0]  s_mem_addr,
    input      [DATA_WIDTH-1:0]  s_mem_wdata,
    input      [WSTRB_WIDTH-1:0] s_mem_wstrb,
    output     [DATA_WIDTH-1:0]  s_mem_rdata

);
    reg [DATA_WIDTH-1:0] mem [0:MEM_SIZE/4-1];

    wire [DATA_WIDTH-1:0] wr_mask;

    genvar i;
    generate
    for (i = 0; i < WSTRB_WIDTH; i=i+1) begin
        assign wr_mask[i*8 +: 8] = {8{s_mem_wstrb[i]}};
    end
    endgenerate
    // assign wr_mask[0 +: 8] = s_mem_wstrb[0] ? 8'hFF : 8'h00; 
    // assign wr_mask[8 +: 8] = s_mem_wstrb[1] ? 8'hFF : 8'h00; 
    // assign wr_mask[16 +: 8] = s_mem_wstrb[2] ? 8'hFF : 8'h00; 
    // assign wr_mask[24 +: 8] = s_mem_wstrb[3] ? 8'hFF : 8'h00; 

    assign s_mem_ready = 1'b1;
    assign s_mem_rdata = mem[s_mem_addr>>2];

    integer j;
    always @(posedge clk or negedge rstn) begin
        if (!rstn) begin
            // for (j=0; j < MEM_SIZE; j=j+1) begin
            //     mem[j] <= {DATA_WIDTH{1'b0}};
            // end
        end
        else begin
            if (s_mem_valid && s_mem_ready) begin // READ operation
                if (s_mem_wstrb > 0) begin 
                    mem[s_mem_addr>>2] <= s_mem_wdata & wr_mask;
                end 

            end
        end

    end

endmodule
