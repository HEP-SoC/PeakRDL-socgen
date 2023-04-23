module pulpif2axi_lite 
#(
    parameter ADDR_WIDTH = 32,
    parameter DATA_WIDTH = 32,
    parameter ID_WIDTH = 2
    


    )(
    input clk,
    input rstn,

    input                         mem_req,
    output                        mem_gnt,
    input                         mem_we,
    input        [ 3:0]           mem_be,
    input        [ADDR_WIDTH-1:0] mem_addr,
    input        [DATA_WIDTH-1:0] mem_wdata,
    input        [7:0]            mem_wdata_intg,
    output                        mem_rvalid,
    output       [DATA_WIDTH-1:0] mem_rdata,
    output       [7:0]            mem_rdata_intg,
    output                        mem_err,

    // AXI
    
    output	wire	[ADDR_WIDTH-1:0]	M_AXI_AWADDR,
    output	wire	[2:0]			    M_AXI_AWPROT,
    output	wire	     			    M_AXI_AWVALID,
    input	wire	     			    M_AXI_AWREADY,
    
    //
    output	wire	[DATA_WIDTH-1:0]	M_AXI_WDATA,
    output	wire	[DATA_WIDTH/8-1:0]	M_AXI_WSTRB,
    output	wire	     			    M_AXI_WVALID,
    input	wire	     			    M_AXI_WREADY,
    //
    input	wire	[1:0]			    M_AXI_BRESP,
    input	wire	     			    M_AXI_BVALID,
    output	wire	     			    M_AXI_BREADY,
    // }}}
    // Read channel master outputs to the connected AXI slaves

    output	wire	[ADDR_WIDTH-1:0]	M_AXI_ARADDR,
    output	wire	     			    M_AXI_ARVALID,
    output	wire	[2:0]			    M_AXI_ARPROT,
    input	wire	     			    M_AXI_ARREADY,

    //
    input	wire	[DATA_WIDTH-1:0]	M_AXI_RDATA,
    input	wire	[1:0]			    M_AXI_RRESP,
    input	wire	     			    M_AXI_RVALID,
    output	wire	     			    M_AXI_RREADY



    );

    `AXI_LITE_TYPEDEF_ALL(axi, logic [ADDR_WIDTH-1:0], logic [DATA_WIDTH-1:0], logic [DATA_WIDTH/8-1:0])

    axi_req_t mst_req;
    axi_resp_t mst_rsp;

    axi_lite_from_mem #(
        .MemAddrWidth ( ADDR_WIDTH    ),
        .AxiAddrWidth ( ADDR_WIDTH    ),
        .DataWidth    ( DATA_WIDTH ),
        .MaxRequests  ( 4 ),
        .AxiProt      ( '0 ),
        .axi_req_t    ( axi_req_t ),
        .axi_rsp_t    ( axi_resp_t )
      ) i_dbg_sba_axi_from_mem (
        .clk_i           ( clk ),
        .rst_ni          ( rstn ),
        .mem_req_i       ( mem_req    ),
        .mem_addr_i      ( mem_addr   ),
        .mem_we_i        ( mem_we     ),
        .mem_wdata_i     ( mem_wdata  ),
        .mem_be_i        ( mem_be   ),
        .mem_gnt_o       ( mem_gnt    ),
        .mem_rsp_valid_o ( mem_rvalid ),
        .mem_rsp_rdata_o ( mem_rdata  ),
        .mem_rsp_error_o ( mem_err    ),
        .axi_req_o       ( mst_req ),
        .axi_rsp_i       ( mst_rsp )
      );

    assign M_AXI_AWADDR = mst_req.aw.addr;
    assign M_AXI_AWPROT = mst_req.aw.prot;
    assign M_AXI_AWVALID = mst_req.aw_valid;
    assign mst_rsp.aw_ready = M_AXI_AWREADY;

    assign M_AXI_WDATA = mst_req.w.data;
    assign M_AXI_WSTRB = mst_req.w.strb;
    assign M_AXI_WVALID = mst_req.w_valid;
    assign mst_rsp.w_ready = M_AXI_WREADY;

    assign mst_rsp.b.resp =  M_AXI_BRESP;
    assign mst_rsp.b_valid =  M_AXI_BVALID;
    assign M_AXI_BREADY = mst_req.b_ready;

    assign M_AXI_ARADDR = mst_req.ar.addr;
    assign M_AXI_ARPROT = mst_req.ar.prot;
    assign M_AXI_ARVALID = mst_req.ar_valid;
    assign mst_rsp.ar_ready = M_AXI_ARREADY;


    assign mst_rsp.r.data = M_AXI_RDATA;
    assign mst_rsp.r.resp = M_AXI_RRESP;
    assign mst_rsp.r_valid = M_AXI_RVALID;
    assign M_AXI_RREADY = mst_req.r_ready;


endmodule

