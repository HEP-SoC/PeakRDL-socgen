module nmi_master #(
    parameter ADDR_WIDTH = 32,
    parameter DATA_WIDTH = 32,

    parameter PROGRST_ADDR = 16,

    parameter WSTRB_WIDTH = (DATA_WIDTH-1)/8+1 // 4 bits for 32 data
    
    ) (
    input clk,
    input rstn,

    output reg m_mem_valid,
    input  m_mem_ready,
    output m_mem_instr,
    output reg  [ADDR_WIDTH-1:0] m_mem_addr,
    output  [DATA_WIDTH-1:0] m_mem_wdata,
    input  [DATA_WIDTH-1:0] m_mem_rdata,
    output  [WSTRB_WIDTH-1:0] m_mem_wstrb
    );


    reg req_reg;

    reg [31:0] counter;

    assign m_mem_wdata = m_mem_addr + 1000;
    assign m_mem_wstrb = 4'hf;

    always @(posedge clk) begin
        if(!rstn) begin 
            m_mem_addr = 0;
        end else begin
            m_mem_addr = m_mem_addr + 1;
        end
    end

    
    always @(posedge clk) begin
        if(!rstn) begin 
            req_reg = 1'b0;
        end else begin

        end
    end

    always @(posedge clk) begin
        if(!rstn) begin 
            m_mem_valid = 1'b0;
        end else begin

            if(req_reg) begin
                m_mem_valid = 1'b1;
            end

        end
    end

    always @(posedge clk) begin
        req_reg <= 1'b1;
    end

endmodule
