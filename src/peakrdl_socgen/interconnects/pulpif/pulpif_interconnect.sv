// TODO PLACEHOLDER FOR REAL CROSSBAR

// Copyright lowRISC contributors.
// Licensed under the Apache License, Version 2.0, see LICENSE for details.
// SPDX-License-Identifier: Apache-2.0

/**
 * Simplistic Ibex bus implementation
 *
 * This module is designed for demo and simulation purposes, do not use it in
 * a real-world system.
 *
 * This implementation doesn't handle the full bus protocol, but makes the
 * following simplifying assumptions.
 *
 * - All devices (slaves) must respond in the next cycle after the request.
 * - Host (master) arbitration is strictly priority based.
 */
module pulpif_interconnect #(
  parameter int N_MASTERS    = 1,
  parameter int N_SLAVES      = 1,
  parameter int DATA_WIDTH    = 32,
  parameter int ADDR_WIDTH = 32,

  parameter STRB_WIDTH = DATA_WIDTH/8,

  parameter [N_MASTERS*ADDR_WIDTH-1:0] SLAVE_ADDR,
  parameter [N_MASTERS*ADDR_WIDTH-1:0] SLAVE_MASK

) (
  input                           clk_i,
  input                           rst_ni,

  // Hosts (masters)
input  [N_SLAVES-1:0]                host_req,
output reg [N_SLAVES-1:0]            host_gnt,
input  [N_SLAVES*ADDR_WIDTH-1:0]     host_addr,
input  [N_SLAVES-1:0]                host_we,
input  [N_SLAVES*STRB_WIDTH-1:0]     host_be,
input  [N_SLAVES*DATA_WIDTH-1:0]     host_wdata,
input  [N_SLAVES*8-1:0]              host_wdata_intg,
output reg [N_SLAVES-1:0]            host_rvalid,
output reg [N_SLAVES*DATA_WIDTH-1:0] host_rdata,
output [N_SLAVES*8-1:0]              host_rdata_intg,
output [N_SLAVES-1:0]                host_err,

 //    Devices                    (slaves)
output reg [N_MASTERS-1:0]            device_req,
input  [N_MASTERS-1:0]                device_gnt,
output reg [N_MASTERS*ADDR_WIDTH-1:0] device_addr,
output reg [N_MASTERS-1:0]            device_we,
output [N_MASTERS*STRB_WIDTH-1:0]     device_be,
output reg [N_MASTERS*DATA_WIDTH-1:0] device_wdata,
output [N_MASTERS*8-1:0]              device_wdata_intg,
input  [N_MASTERS-1:0]                device_rvalid,
input  [N_MASTERS*DATA_WIDTH-1:0]     device_rdata,
input  [N_MASTERS*8-1:0]              device_rdata_intg,
input  [N_MASTERS-1:0]                device_err

  // Device address map
);

  localparam int unsigned NumBitsHostSel = N_SLAVES > 1 ? $clog2(N_SLAVES) : 1;
  localparam int unsigned NumBitsDeviceSel = N_MASTERS > 1 ? $clog2(N_MASTERS) : 1;

  logic [NumBitsHostSel-1:0] host_sel_req, host_sel_resp;
  logic [NumBitsDeviceSel-1:0] device_sel_req, device_sel_resp;

  // Master select prio arbiter
  always_comb begin
    host_sel_req = '0;
    for (integer host = N_SLAVES - 1; host >= 0; host = host - 1) begin
      if (host_req[host]) begin
        host_sel_req = NumBitsHostSel'(host);
      end
    end
  end

  // Device select
  always_comb begin
    device_sel_req = '0;
    for (integer device = 0; device < N_MASTERS; device = device + 1) begin
      if ((host_addr[host_sel_req*ADDR_WIDTH +: ADDR_WIDTH] & SLAVE_MASK[device*ADDR_WIDTH +: ADDR_WIDTH])
          == SLAVE_ADDR[device*ADDR_WIDTH +: ADDR_WIDTH]) begin
          /* == cfg_device_addr_base[device]) begin */
        device_sel_req = NumBitsDeviceSel'(device);
      end
    end
  end

  always_ff @(posedge clk_i or negedge rst_ni) begin
     if (!rst_ni) begin
        host_sel_resp <= '0;
        device_sel_resp <= '0;
     end else begin
        // Responses are always expected 1 cycle after the request
        device_sel_resp <= device_sel_req;
        host_sel_resp <= host_sel_req;
     end
  end

  always_comb begin
    for (integer device = 0; device < N_MASTERS; device = device + 1) begin
      if (NumBitsDeviceSel'(device) == device_sel_req) begin
        device_req[device]                            = host_req[host_sel_req];
        device_we[device]                             = host_we[host_sel_req];
        device_addr[device*ADDR_WIDTH +: ADDR_WIDTH]  = host_addr[host_sel_req*ADDR_WIDTH +: ADDR_WIDTH];
        device_wdata[device*DATA_WIDTH +: DATA_WIDTH] = host_wdata[host_sel_req*DATA_WIDTH +: DATA_WIDTH];
        device_be[device*STRB_WIDTH +: STRB_WIDTH]    = host_be[host_sel_req*STRB_WIDTH +: STRB_WIDTH];
      end else begin
        device_req[device]                            = 1'b0;
        device_we[device]                             = 1'b0;
        device_addr[device*ADDR_WIDTH +: ADDR_WIDTH]  = 'b0;
        device_wdata[device*DATA_WIDTH +: DATA_WIDTH] = 'b0;
        device_be[device*STRB_WIDTH +: STRB_WIDTH]    = 'b0;
      end
    end
  end

  always_comb begin
    for (integer host = 0; host < N_SLAVES; host = host + 1) begin
      host_gnt[host] = 1'b0;
      if (NumBitsHostSel'(host) == host_sel_resp) begin
        host_rvalid[host]                         = device_rvalid[device_sel_resp];
        host_err[host]                            = device_err[device_sel_resp];
        host_rdata[host*DATA_WIDTH +: DATA_WIDTH] = device_rdata[device_sel_resp*DATA_WIDTH +: DATA_WIDTH];
      end else begin
        host_rvalid[host]                         = 1'b0;
        host_err[host]                            = 1'b0;
        host_rdata[host*DATA_WIDTH +: DATA_WIDTH] = 'b0;
      end
    end
    host_gnt[host_sel_req] = host_req[host_sel_req];
  end
endmodule

