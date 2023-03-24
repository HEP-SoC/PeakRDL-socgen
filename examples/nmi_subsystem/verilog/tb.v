module tb();

    reg clk = 1'b0;
    reg rstn = 1'b1;

    initial begin
        $dumpfile("test1.vcd");
        $dumpvars();
        @(posedge clk);
        rstn = 1'b0;
        @(posedge clk);
        @(posedge clk);
        rstn = 1'b1;

        #10000000;
        $finish();
    end

    always begin
        clk <= !clk;
        #10;
    end

    nmi_subsystem sub (.clk(clk), .rstn(rstn));

endmodule
