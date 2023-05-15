module majorityVoter #(
  parameter WIDTH = 1
)( 
  input wire  [3*WIDTH-1:0] in,
  output wire [WIDTH-1:0]   out
);
  assign out = (in[0 +: WIDTH]&in[1*WIDTH +: WIDTH]) | (in[0 +: WIDTH]&in[2*WIDTH +: WIDTH]) | (in[1*WIDTH +: WIDTH]&in[2*WIDTH +: WIDTH]);
  // always @(in[0 +: WIDTH] or in[1*WIDTH +: WIDTH] or in[2*WIDTH +: WIDTH]) begin
    // if (in[0 +: WIDTH]!=in[1*WIDTH +: WIDTH] || in[0 +: WIDTH]!=in[2*WIDTH +: WIDTH] || in[1*WIDTH +: WIDTH]!=in[2*WIDTH +: WIDTH])
    //   tmrErr = 1;
    // else
    //   tmrErr = 0;
  // end
endmodule

