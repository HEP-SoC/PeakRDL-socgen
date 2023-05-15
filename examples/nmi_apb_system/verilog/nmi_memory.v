module nmi_memory #(
        parameter ADDR_WIDTH = 32,
        parameter DATA_WIDTH = 32,
        parameter MEM_SIZE = 2048,
        parameter ID = 0,


        parameter WSTRB_WIDTH = (DATA_WIDTH-1)/8+1 // 4 bits for 32 data
    )(
    input  clk,
    input  rstn,

    input  s_nmi_valid,
    input  s_nmi_instr,
    output s_nmi_ready,

    input      [ADDR_WIDTH-1:0]  s_nmi_addr,
    input      [DATA_WIDTH-1:0]  s_nmi_wdata,
    input      [WSTRB_WIDTH-1:0] s_nmi_wstrb,
    output     [DATA_WIDTH-1:0]  s_nmi_rdata

);
    reg [DATA_WIDTH-1:0] mem [0:MEM_SIZE/4-1];

    wire [DATA_WIDTH-1:0] wr_mask;

    genvar i;
    generate
    for (i = 0; i < WSTRB_WIDTH; i=i+1) begin
        assign wr_mask[i*8 +: 8] = {8{s_nmi_wstrb[i]}};
    end
    endgenerate

    assign s_nmi_ready = 1'b1;
    assign s_nmi_rdata = mem[s_nmi_addr>>2]; //(mem[s_nmi_addr>>2] & 32'h00FFFFFF) | (ID << 24); // Append ID up for recognition

    integer j;
    always @(posedge clk or negedge rstn) begin
        if (!rstn) begin
            // for (j=0; j < MEM_SIZE; j=j+1) begin
            //     mem[j] <= {DATA_WIDTH{1'b0}};
            // end
        end
        else begin
            if (s_nmi_valid && s_nmi_ready) begin // READ operation
                if (s_nmi_wstrb > 0) begin 
                    mem[s_nmi_addr>>2] <= s_nmi_wdata & wr_mask;
                end 

            end
        end

    end

endmodule
