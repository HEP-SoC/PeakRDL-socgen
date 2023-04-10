`timescale 1 ns / 1 ps
module picorvino_wrap (
    input clk,
    input rstn
);

	string firmware_file;
	initial begin
        if (!$value$plusargs("firmware=%s", firmware_file)) begin
            $display("Error, need to give a firmware file to run\n");
            $finish;
        end
        $display("Firmware file: %s", firmware_file);
		
        $readmemh(firmware_file, picorvino_i.mem0.mem);
	end

    picorvino picorvino_i(
        .clk(clk),
        .rstn(rstn)
    );

endmodule

