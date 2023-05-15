module fanout #(
  parameter WIDTH = 1
)(
  input wire  [WIDTH-1:0] in,
  output wire [3*WIDTH-1:0] out
);
  assign out[0 +: WIDTH] = in;
  assign out[1*WIDTH +: WIDTH] = in;
  assign out[2*WIDTH +: WIDTH] = in;
endmodule


