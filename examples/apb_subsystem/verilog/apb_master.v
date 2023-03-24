module apb_master #(
    parameter ADDR_WIDTH = 32,
    parameter DATA_WIDTH = 32,

    parameter WSTRB_WIDTH = (DATA_WIDTH-1)/8+1 // 4 bits for 32 data
    
    ) (
    input clk,
    input rstn,

    output reg m_penable,
    output  m_pwrite,
    output reg m_psel,
    output reg [ADDR_WIDTH-1:0] m_paddr,
    output  [DATA_WIDTH-1:0] m_pwdata,
    output  [WSTRB_WIDTH-1:0] m_pstrb,
    input wire [DATA_WIDTH-1:0] m_prdata,
    input wire                  m_pready,
    input wire                  m_pslverr
    );


    reg req_reg;

    reg [31:0] counter;

    assign m_pwdata = m_paddr + 1000;
    assign m_pstrb = 4'hf;
    assign m_pwrite = 1'b1;

    always @(posedge clk) begin
        if(!rstn) begin 
            m_paddr <= 0;
        end else begin
            m_paddr <= m_paddr + 1;
        end
    end

    
    always @(posedge clk) begin
        if(!rstn) begin 
            req_reg <= 1'b0;
        end else begin
            req_reg <= 1'b1;
        end
    end

    reg [1:0] cnt;

    always @(posedge clk) begin
        if(!rstn) begin 
            m_psel <= 1'b0;
            m_penable <= 1'b0;
            cnt <= 2'b00;
        end else begin
            cnt <= cnt+1;

            if(cnt == 0 || cnt == 1) begin
                m_penable <= 1'b1;
            end else begin
                m_penable <= 1'b0;
            end

            if(cnt == 1) begin
                m_psel <= 1'b1;
            end  else begin
                m_psel <= 1'b0;
            end
            
        end
    end

endmodule
