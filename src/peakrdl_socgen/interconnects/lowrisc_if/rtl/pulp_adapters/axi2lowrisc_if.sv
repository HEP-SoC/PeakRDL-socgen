// Copyright 2015 ETH Zurich and University of Bologna.
// Copyright and related rights are licensed under the Solderpad Hardware
// License, Version 0.51 (the “License”); you may not use this file except in
// compliance with the License.  You may obtain a copy of the License at
// http://solderpad.org/licenses/SHL-0.51. Unless required by applicable law
// or agreed to in writing, software, hardware and materials distributed under
// this License is distributed on an “AS IS” BASIS, WITHOUT WARRANTIES OR
// CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

module axi2lowrisc_if
#(
    parameter ADDR_WIDTH = 32,
    parameter DATA_WIDTH   = 32,
    parameter AXI4_ID_WIDTH      = 16,
    parameter AXI4_USER_WIDTH    = 10,
    parameter AXI_NUMBYTES       = DATA_WIDTH/8,
    parameter MEM_ADDR_WIDTH     = 13,
    parameter BUFF_DEPTH_SLAVE   = 4
)
(
    input logic                                     ACLK,
    input logic                                     ARESETn,


    // ---------------------------------------------------------
    // AXI TARG Port Declarations ------------------------------
    // ---------------------------------------------------------
    //AXI write address bus -------------- // USED// -----------
    input  logic [AXI4_ID_WIDTH-1:0]                S_AWID     ,
    input  logic [ADDR_WIDTH-1:0]                   S_AWADDR   ,
    input  logic [ 7:0]                             S_AWLEN    ,
    input  logic [ 2:0]                             S_AWSIZE   ,
    input  logic [ 1:0]                             S_AWBURST  ,
    input  logic                                    S_AWLOCK   ,
    input  logic [ 3:0]                             S_AWCACHE  ,
    input  logic [ 2:0]                             S_AWPROT   ,
    input  logic [ 3:0]                             S_AWREGION ,
    input  logic [ AXI4_USER_WIDTH-1:0]             S_AWUSER   ,
    input  logic [ 3:0]                             S_AWQOS    ,
    input  logic                                    S_AWVALID  ,
    output logic                                    S_AWREADY  ,
    // ---------------------------------------------------------

    //AXI write data bus -------------- // USED// --------------
    input  logic [AXI_NUMBYTES-1:0][7:0]            S_WDATA    ,
    input  logic [AXI_NUMBYTES-1:0]                 S_WSTRB    ,
    input  logic                                    S_WLAST    ,
    input  logic [AXI4_USER_WIDTH-1:0]              S_WUSER    ,
    input  logic                                    S_WVALID   ,
    output logic                                    S_WREADY   ,
    // ---------------------------------------------------------

    //AXI write response bus -------------- // USED// ----------
    output logic   [AXI4_ID_WIDTH-1:0]              S_BID      ,
    output logic   [ 1:0]                           S_BRESP    ,
    output logic                                    S_BVALID   ,
    output logic   [AXI4_USER_WIDTH-1:0]            S_BUSER    ,
    input  logic                                    S_BREADY   ,
    // ---------------------------------------------------------

    //AXI read address bus -------------------------------------
    input  logic [AXI4_ID_WIDTH-1:0]                S_ARID     ,
    input  logic [ADDR_WIDTH-1:0]                   S_ARADDR   ,
    input  logic [ 7:0]                             S_ARLEN    ,
    input  logic [ 2:0]                             S_ARSIZE   ,
    input  logic [ 1:0]                             S_ARBURST  ,
    input  logic                                    S_ARLOCK   ,
    input  logic [ 3:0]                             S_ARCACHE  ,
    input  logic [ 2:0]                             S_ARPROT   ,
    input  logic [ 3:0]                             S_ARREGION ,
    input  logic [ AXI4_USER_WIDTH-1:0]             S_ARUSER   ,
    input  logic [ 3:0]                             S_ARQOS    ,
    input  logic                                    S_ARVALID  ,
    output logic                                    S_ARREADY  ,
    // ---------------------------------------------------------

    //AXI read data bus ----------------------------------------
    output  logic [AXI4_ID_WIDTH-1:0]               S_RID      ,
    output  logic [DATA_WIDTH-1:0]                  S_RDATA    ,
    output  logic [ 1:0]                            S_RRESP    ,
    output  logic                                   S_RLAST    ,
    output  logic [AXI4_USER_WIDTH-1:0]             S_RUSER    ,
    output  logic                                   S_RVALID   ,
    input   logic                                   S_RREADY   ,
    // ---------------------------------------------------------

    output logic                        lowrisc_req,
    output logic [ADDR_WIDTH-1:0]       lowrisc_addr,
    output logic                        lowrisc_we,
    input  logic                        lowrisc_gnt,
    input  logic                        lowrisc_rvalid,
    input  logic                        lowrisc_err,
    output logic [DATA_WIDTH/8-1:0]     lowrisc_be,
    input  logic [DATA_WIDTH-1:0]       lowrisc_rdata,
    input  logic [7:0]                  lowrisc_rdata_intg,
    output logic [DATA_WIDTH-1:0]       lowrisc_wdata,
    output logic [7:0]                  lowrisc_wdata_intg,

);
    wire test_en_i;
    assign test_en_i = 1'b0;

    logic                              CEN_o;
    logic                              WEN_o;
    logic  [MEM_ADDR_WIDTH-1:0]        A_o;
    logic  [DATA_WIDTH-1:0]            D_o;
    logic  [AXI_NUMBYTES-1:0]          BE_o;
    logic  [DATA_WIDTH-1:0]            Q_i;

    assign lowrisc_req = ~CEN_o;
    assign lowrisc_we = ~WEN_o;
    assign lowrisc_addr = A_o;
    assign lowrisc_wdata = D_o;
    assign lowrisc_be = BE_o;
    assign lowrisc_rdata = Q_i;

    logic valid_R, valid_W;
    logic grant_R, grant_W;
    logic RR_FLAG;

	// -----------------------------------------------------------
	// AXI TARG Port Declarations --------------------------------
	// -----------------------------------------------------------
	//AXI write address bus --------------------------------------
	logic [AXI4_ID_WIDTH-1:0]                         AWID     ;
	logic [ADDR_WIDTH-1:0]                            AWADDR   ;
	logic [ 7:0]                                      AWLEN    ;
	logic [ 2:0]                                      AWSIZE   ;
	logic [ 1:0]                                      AWBURST  ;
	logic                                             AWLOCK   ;
	logic [ 3:0]                                      AWCACHE  ;
	logic [ 2:0]                                      AWPROT   ;
	logic [ 3:0]                                      AWREGION ;
	logic [ AXI4_USER_WIDTH-1:0]                      AWUSER   ;
	logic [ 3:0]                                      AWQOS    ;
	logic                                             AWVALID  ;
	logic                                             AWREADY  ;
	// -----------------------------------------------------------
	//AXI write data bus ------------------------ ----------------
	logic [AXI_NUMBYTES-1:0][7:0]                     WDATA    ;
	logic [AXI_NUMBYTES-1:0]                          WSTRB    ;
	logic                                             WLAST    ;
	logic [AXI4_USER_WIDTH-1:0]                       WUSER    ;
	logic                                             WVALID   ;
	logic                                             WREADY   ;
	// -----------------------------------------------------------
	//AXI write response bus -------------------------------------
	logic   [AXI4_ID_WIDTH-1:0]                       BID      ;
	logic   [ 1:0]                                    BRESP    ;
	logic                                             BVALID   ;
	logic   [AXI4_USER_WIDTH-1:0]                     BUSER    ;
	logic                                             BREADY   ;
	// -----------------------------------------------------------
	//AXI read address bus ---------------------------------------
	logic [AXI4_ID_WIDTH-1:0]                         ARID     ;
	logic [ADDR_WIDTH-1:0]                            ARADDR   ;
	logic [ 7:0]                                      ARLEN    ;
	logic [ 2:0]                                      ARSIZE   ;
	logic [ 1:0]                                      ARBURST  ;
	logic                                             ARLOCK   ;
	logic [ 3:0]                                      ARCACHE  ;
	logic [ 2:0]                                      ARPROT   ;
	logic [ 3:0]                                      ARREGION ;
	logic [ AXI4_USER_WIDTH-1:0]                      ARUSER   ;
	logic [ 3:0]                                      ARQOS    ;
	logic                                             ARVALID  ;
	logic                                             ARREADY  ;
	// -----------------------------------------------------------
	//AXI read data bus ------------------------------------------
	logic [AXI4_ID_WIDTH-1:0]                         RID      ;
	logic [DATA_WIDTH-1:0]                            RDATA    ;
	logic [ 1:0]                                      RRESP    ;
	logic                                             RLAST    ;
	logic [AXI4_USER_WIDTH-1:0]                       RUSER    ;
	logic                                             RVALID   ;
	logic                                             RREADY   ;
	// -----------------------------------------------------------


    logic                         W_cen    , R_cen    ;
    logic                         W_wen    , R_wen    ;
    logic [MEM_ADDR_WIDTH-1:0]    W_addr   , R_addr   ;
    logic [DATA_WIDTH-1:0]  W_wdata  , R_wdata  ;
    logic [AXI_NUMBYTES-1:0]      W_be     , R_be     ;


    // AXI WRITE ADDRESS CHANNEL BUFFER
    axi_aw_buffer
    #(
       .ID_WIDTH     ( AXI4_ID_WIDTH      ),
       .ADDR_WIDTH   ( ADDR_WIDTH ),
       .USER_WIDTH   ( AXI4_USER_WIDTH    ),
       .BUFFER_DEPTH ( BUFF_DEPTH_SLAVE   )
    )
    Slave_aw_buffer_LP
    (
      .clk_i           ( ACLK        ),
      .rst_ni          ( ARESETn     ),
      .test_en_i       ( test_en_i   ),

      .slave_valid_i   ( S_AWVALID   ),
      .slave_addr_i    ( S_AWADDR    ),
      .slave_prot_i    ( S_AWPROT    ),
      .slave_region_i  ( S_AWREGION  ),
      .slave_len_i     ( S_AWLEN     ),
      .slave_size_i    ( S_AWSIZE    ),
      .slave_burst_i   ( S_AWBURST   ),
      .slave_lock_i    ( S_AWLOCK    ),
      .slave_cache_i   ( S_AWCACHE   ),
      .slave_qos_i     ( S_AWQOS     ),
      .slave_id_i      ( S_AWID      ),
      .slave_user_i    ( S_AWUSER    ),
      .slave_ready_o   ( S_AWREADY   ),

      .master_valid_o  ( AWVALID     ),
      .master_addr_o   ( AWADDR      ),
      .master_prot_o   ( AWPROT      ),
      .master_region_o ( AWREGION    ),
      .master_len_o    ( AWLEN       ),
      .master_size_o   ( AWSIZE      ),
      .master_burst_o  ( AWBURST     ),
      .master_lock_o   ( AWLOCK      ),
      .master_cache_o  ( AWCACHE     ),
      .master_qos_o    ( AWQOS       ),
      .master_id_o     ( AWID        ),
      .master_user_o   ( AWUSER      ),
      .master_ready_i  ( AWREADY     )
    );


   // AXI WRITE ADDRESS CHANNEL BUFFER
   axi_ar_buffer
   #(
       .ID_WIDTH     ( AXI4_ID_WIDTH      ),
       .ADDR_WIDTH   ( ADDR_WIDTH ),
       .USER_WIDTH   ( AXI4_USER_WIDTH    ),
       .BUFFER_DEPTH ( BUFF_DEPTH_SLAVE   )
   )
   Slave_ar_buffer_LP
   (
      .clk_i           ( ACLK       ),
      .rst_ni          ( ARESETn    ),
      .test_en_i       ( test_en_i  ),

      .slave_valid_i   ( S_ARVALID  ),
      .slave_addr_i    ( S_ARADDR   ),
      .slave_prot_i    ( S_ARPROT   ),
      .slave_region_i  ( S_ARREGION ),
      .slave_len_i     ( S_ARLEN    ),
      .slave_size_i    ( S_ARSIZE   ),
      .slave_burst_i   ( S_ARBURST  ),
      .slave_lock_i    ( S_ARLOCK   ),
      .slave_cache_i   ( S_ARCACHE  ),
      .slave_qos_i     ( S_ARQOS    ),
      .slave_id_i      ( S_ARID     ),
      .slave_user_i    ( S_ARUSER   ),
      .slave_ready_o   ( S_ARREADY  ),

      .master_valid_o  ( ARVALID    ),
      .master_addr_o   ( ARADDR     ),
      .master_prot_o   ( ARPROT     ),
      .master_region_o ( ARREGION   ),
      .master_len_o    ( ARLEN      ),
      .master_size_o   ( ARSIZE     ),
      .master_burst_o  ( ARBURST    ),
      .master_lock_o   ( ARLOCK     ),
      .master_cache_o  ( ARCACHE    ),
      .master_qos_o    ( ARQOS      ),
      .master_id_o     ( ARID       ),
      .master_user_o   ( ARUSER     ),
      .master_ready_i  ( ARREADY    )
   );


   axi_w_buffer
   #(
       .DATA_WIDTH(DATA_WIDTH),
       .USER_WIDTH(AXI4_USER_WIDTH),
       .BUFFER_DEPTH(BUFF_DEPTH_SLAVE)
   )
   Slave_w_buffer_LP
   (
        .clk_i          ( ACLK      ),
        .rst_ni         ( ARESETn   ),
        .test_en_i      ( test_en_i ),

        .slave_valid_i  ( S_WVALID  ),
        .slave_data_i   ( S_WDATA   ),
        .slave_strb_i   ( S_WSTRB   ),
        .slave_user_i   ( S_WUSER   ),
        .slave_last_i   ( S_WLAST   ),
        .slave_ready_o  ( S_WREADY  ),

        .master_valid_o ( WVALID    ),
        .master_data_o  ( WDATA     ),
        .master_strb_o  ( WSTRB     ),
        .master_user_o  ( WUSER     ),
        .master_last_o  ( WLAST     ),
        .master_ready_i ( WREADY    )
    );

   axi_r_buffer
   #(
        .ID_WIDTH(AXI4_ID_WIDTH),
        .DATA_WIDTH(DATA_WIDTH),
        .USER_WIDTH(AXI4_USER_WIDTH),
        .BUFFER_DEPTH(BUFF_DEPTH_SLAVE)
   )
   Slave_r_buffer_LP
   (
        .clk_i          ( ACLK       ),
        .rst_ni         ( ARESETn    ),
        .test_en_i      ( test_en_i  ),

        .slave_valid_i  ( RVALID     ),
        .slave_data_i   ( RDATA      ),
        .slave_resp_i   ( RRESP      ),
        .slave_user_i   ( RUSER      ),
        .slave_id_i     ( RID        ),
        .slave_last_i   ( RLAST      ),
        .slave_ready_o  ( RREADY     ),

        .master_valid_o ( S_RVALID   ),
        .master_data_o  ( S_RDATA    ),
        .master_resp_o  ( S_RRESP    ),
        .master_user_o  ( S_RUSER    ),
        .master_id_o    ( S_RID      ),
        .master_last_o  ( S_RLAST    ),
        .master_ready_i ( S_RREADY   )
   );

   axi_b_buffer
   #(
        .ID_WIDTH(AXI4_ID_WIDTH),
        .USER_WIDTH(AXI4_USER_WIDTH),
        .BUFFER_DEPTH(BUFF_DEPTH_SLAVE)
   )
   Slave_b_buffer_LP
   (
        .clk_i          ( ACLK      ),
        .rst_ni         ( ARESETn   ),
        .test_en_i      ( test_en_i ),

        .slave_valid_i  ( BVALID    ),
        .slave_resp_i   ( BRESP     ),
        .slave_id_i     ( BID       ),
        .slave_user_i   ( BUSER     ),
        .slave_ready_o  ( BREADY    ),

        .master_valid_o ( S_BVALID  ),
        .master_resp_o  ( S_BRESP   ),
        .master_id_o    ( S_BID     ),
        .master_user_o  ( S_BUSER   ),
        .master_ready_i ( S_BREADY  )
   );


	// High Priority Write FSM
	axi_write_only_ctrl
	#(
	    .AXI4_ADDRESS_WIDTH ( ADDR_WIDTH  ),
	    .AXI4_RDATA_WIDTH   ( DATA_WIDTH    ),
	    .AXI4_WDATA_WIDTH   ( DATA_WIDTH    ),
	    .AXI4_ID_WIDTH      ( AXI4_ID_WIDTH       ),
	    .AXI4_USER_WIDTH    ( AXI4_USER_WIDTH     ),
	    .AXI_NUMBYTES       ( AXI_NUMBYTES        ),
	    .MEM_ADDR_WIDTH     ( MEM_ADDR_WIDTH      )
	)
	WRITE_CTRL
	(
	    .clk            (  ACLK         ),
	    .rst_n          (  ARESETn      ),

	    .AWID_i         (  AWID         ),
	    .S_AWADDR       (  AWADDR       ),
	    .AWLEN_i        (  AWLEN        ),
	    .AWSIZE_i       (  AWSIZE       ),
	    .AWBURST_i      (  AWBURST      ),
	    .AWLOCK_i       (  AWLOCK       ),
	    .AWCACHE_i      (  AWCACHE      ),
	    .AWPROT_i       (  AWPROT       ),
	    .AWREGION_i     (  AWREGION     ),
	    .AWUSER_i       (  AWUSER       ),
	    .AWQOS_i        (  AWQOS        ),
	    .AWVALID_i      (  AWVALID      ),
	    .AWREADY_o      (  AWREADY      ),

	    //AXI write data bus ------   -------- // USED// -------------
	    .WDATA_i        (  WDATA         ),
	    .WSTRB_i        (  WSTRB         ),
	    .WLAST_i        (  WLAST         ),
	    .WUSER_i        (  WUSER         ),
	    .WVALID_i       (  WVALID        ),
	    .WREADY_o       (  WREADY        ),

	    //AXI write response bus --   ------------ // USED// ----------
	    .BID_o          (  BID           ),
	    .BRESP_o        (  BRESP         ),
	    .BVALID_o       (  BVALID        ),
	    .BUSER_o        (  BUSER         ),
	    .BREADY_i       (  BREADY        ),

	    .MEM_CEN_o      (  W_cen         ),
	    .MEM_WEN_o      (  W_wen         ),
	    .MEM_A_o        (  W_addr        ),
	    .MEM_D_o        (  W_wdata       ),
	    .MEM_BE_o       (  W_be          ),
	    .MEM_Q_i        (  '0            ),

	    .grant_i        (  grant_W       ),
	    .valid_o        (  valid_W       )
	);


	axi_read_only_ctrl
	#(
	    .AXI4_ADDRESS_WIDTH ( ADDR_WIDTH  ),
	    .AXI4_RDATA_WIDTH   ( DATA_WIDTH    ),
	    .AXI4_WDATA_WIDTH   ( DATA_WIDTH    ),
	    .AXI4_ID_WIDTH      ( AXI4_ID_WIDTH       ),
	    .AXI4_USER_WIDTH    ( AXI4_USER_WIDTH     ),
	    .AXI_NUMBYTES       ( AXI_NUMBYTES        ),
	    .MEM_ADDR_WIDTH     ( MEM_ADDR_WIDTH      )
	)
	READ_CTRL
	(
	    .clk            (  ACLK       ),
	    .rst_n          (  ARESETn    ),

	    .ARID_i         (  ARID      ),
	    .ARADDR_i       (  ARADDR    ),
	    .ARLEN_i        (  ARLEN     ),
	    .ARSIZE_i       (  ARSIZE    ),
	    .ARBURST_i      (  ARBURST   ),
	    .ARLOCK_i       (  ARLOCK    ),
	    .ARCACHE_i      (  ARCACHE   ),
	    .ARPROT_i       (  ARPROT    ),
	    .ARREGION_i     (  ARREGION  ),
	    .ARUSER_i       (  ARUSER    ),
	    .ARQOS_i        (  ARQOS     ),
	    .ARVALID_i      (  ARVALID   ),
	    .ARREADY_o      (  ARREADY   ),

	    .RID_o          (  RID       ),
	    .RDATA_o        (  RDATA     ),
	    .RRESP_o        (  RRESP     ),
	    .RLAST_o        (  RLAST     ),
	    .RUSER_o        (  RUSER     ),
	    .RVALID_o       (  RVALID    ),
	    .RREADY_i       (  RREADY    ),

	    .MEM_CEN_o      (  R_cen     ),
	    .MEM_WEN_o      (  R_wen     ),
	    .MEM_A_o        (  R_addr    ),
	    .MEM_D_o        (  R_wdata   ),
	    .MEM_BE_o       (  R_be      ),
	    .MEM_Q_i        (  Q_i       ),

	    .grant_i        (  grant_R   ),
	    .valid_o        (  valid_R   )
	);


	always_comb
	begin : _MUX_MEM_
		  if(valid_R & grant_R)
		  begin
		    CEN_o   = R_cen   ;
		    WEN_o   = 1'b1       ;
		    A_o     = R_addr  ;
		    D_o     = R_wdata ;
		    BE_o    = R_be    ;
		  end
		  else
		  begin
		    CEN_o   = W_cen   ;
		    WEN_o   = 1'b0       ;
		    A_o     = W_addr  ;
		    D_o     = W_wdata ;
		    BE_o    = W_be    ;
		  end
	end


//Low Priority RR Arbiter
always_comb
begin
  grant_R = 1'b0;
  grant_W = 1'b0;

  case (RR_FLAG)

  1'b0: //Priority on Write
  begin
    if(valid_W)
      grant_W = 1'b1;
    else
      grant_R = 1'b1;
  end


  1'b1: //Priority on Read
  begin
    if(valid_R)
      grant_R = 1'b1;
    else
      grant_W = 1'b1;
  end
  endcase
end


always_ff @(posedge ACLK or negedge ARESETn)
begin
  if(~ARESETn) begin
     RR_FLAG <= 0;
  end
  else
  begin
  		if(CEN_o == 1'b0)
      	   RR_FLAG  <= ~RR_FLAG;
  end
end


endmodule // axi_mem_if_SP_32
