module simple_apb_slave #(
    parameter ADDR_WIDTH = 32,
    parameter DATA_WIDTH = 32,
    parameter MEM_SIZE = 32, // UNUSED
    parameter ID = 0,

    parameter WSTRB_WIDTH = (DATA_WIDTH-1)/8+1 // 4 bits for 32 data
    
    ) (
    input clk,
    input rstn,

    input wire s_penable,
    input wire s_pwrite,
    input wire s_psel,
    input wire [ADDR_WIDTH-1:0] s_paddr,
    input wire [DATA_WIDTH-1:0] s_pwdata,
    input wire [WSTRB_WIDTH-1:0] s_pstrb,
    output  [DATA_WIDTH-1:0] s_prdata,
    output                      s_pready,
    output reg                  s_pslverr
    );


    assign s_prdata = ID+1;
    assign s_pready = 1'b1;

    always @(posedge clk) begin
        if(s_penable && s_psel) begin
            $display("Slave ID=%d addr=0x%0h wdata=0x%0h", ID, s_paddr, s_pwdata);
        end
    end

endmodule

