/*
 *  PicoRV32 -- A Small RISC-V (RV32I) Processor Core
 *
 *  Copyright (C) 2015  Claire Xenia Wolf <claire@yosyshq.com>
 *
 *  Permission to use, copy, modify, and/or distribute this software for any
 *  purpose with or without fee is hereby granted, provided that the above
 *  copyright notice and this permission notice appear in all copies.
 *
 *  THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
 *  WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
 *  MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
 *  ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
 *  WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
 *  ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
 *  OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
 *
 */

/*
Reasons for non-voted registers, which are not used and can be optimized in TMR synthesis:
	- alu_out_0_q				used only if TWO_CYCLE_COMPARE = 1
	- cached_ascii_instr		only for simulation debug
	- cached_insn_imm			only for simulation debug 
	- cached_insn_opcode		only for simulation debug
	- cached_insn_rd			only for simulation debug
	- cached_insn_rs1			only for simulation debug
	- cached_insn_rs2			only for simulation debug
	- dbg_insn_addr				only for simulation debug
	- dbg_next					only for simulation debug
	- dbg_rs1val_valid			only for simulation debug
	- dbg_rs1val				only for simulation debug
	- dbg_rs2val_valid			only for simulation debug
	- dbg_rs2val				only for simulation debug
	- dbg_valid_insn			only for simulation debug
	- decoder_pseudo_trigger_q	used only for debug and if CATCH_ILLINSN = 0 
	- decoder_trigger_q			used only for debug and if CATCH_ILLINSN = 0
	- instr_ecall_ebreak		used only if CATCH_ILLINSN = 0 or with PCPI enabled (PCPI, mul or div)
	- next_insn_opcode			only for simulation debug
	- pcpi_insn					used only with PCPI enabled (PCPI, mul or div)
	- pcpi_timeout_counter		used only with PCPI enabled (PCPI, mul or div)
	- pcpi_timeout				used only with PCPI enabled (PCPI, mul or div)
	- pcpi_valid				used only with PCPI enabled (PCPI, mul or div)
	- q_ascii_instr				only for simulation debug
	- q_insn_imm				only for simulation debug
	- q_insn_opcode				only for simulation debug
	- q_insn_rd					only for simulation debug
	- q_insn_rs1				only for simulation debug
	- q_insn_rs2				only for simulation debug
*/

/***************************************************************
 * picorv32
 ***************************************************************/

module picorv32 #(
    parameter [ 0:0] ENABLE_COUNTERS       = 1,
    parameter [ 0:0] ENABLE_COUNTERS64     = 1,
    parameter [ 0:0] ENABLE_REGS_16_31     = 1,
    parameter [ 0:0] ENABLE_REGS_DUALPORT  = 1,
    parameter [ 0:0] LATCHED_MEM_RDATA     = 0,
    parameter [ 0:0] TWO_STAGE_SHIFT       = 1,
    parameter [ 0:0] BARREL_SHIFTER        = 0,
    parameter [ 0:0] TWO_CYCLE_COMPARE     = 0,    // Vote "alu_out_0_q" if set to 1
    parameter [ 0:0] TWO_CYCLE_ALU         = 0,
    parameter [ 0:0] COMPRESSED_ISA        = 1,    // Default: 0
    parameter [ 0:0] CATCH_MISALIGN        = 1,
    parameter [ 0:0] CATCH_ILLINSN         = 1,    // Vote "decoder_pseudo_trigger_q", "decoder_trigger_q", "instr_ecall_ebreak"if set to 0
    parameter [ 0:0] ENABLE_PCPI           = 0,    // Vote "instr_ecall_ebreak", "pcpi_insn" if set to 1
    parameter [ 0:0] ENABLE_MUL            = 0,    // Vote "instr_ecall_ebreak", "pcpi_insn" if set to 1
    parameter [ 0:0] ENABLE_FAST_MUL       = 0,    // Vote "instr_ecall_ebreak", "pcpi_insn" if set to 1
    parameter [ 0:0] ENABLE_DIV            = 0,    // Vote "instr_ecall_ebreak", "pcpi_insn" if set to 1
    parameter [ 0:0] ENABLE_IRQ            = 1,    // Default: 0
    parameter [ 0:0] ENABLE_IRQ_QREGS      = 1,
    parameter [ 0:0] ENABLE_IRQ_TIMER      = 1,
    parameter [ 0:0] ENABLE_TRACE          = 1,    // Default: 0
    parameter [ 0:0] REGS_INIT_ZERO        = 0,
    parameter [31:0] MASKED_IRQ            = 32'h 0000_0000,
    parameter [31:0] LATCHED_IRQ           = 32'h ffff_ffff,
    parameter [31:0] PROGADDR_RESET        = 32'h 0000_0000,           // Default: 32'h 0000_0000
    parameter [31:0] PROGADDR_IRQ          = 32'h 0000_0010,   // Default: 32'h 0000_0010
    parameter [31:0] STACKADDR             = 32'h ffff_ffff
    )(
	input clk, rstn,
	output trap,

	output            m_nmi_valid,
	output            m_nmi_instr,
	input             m_nmi_ready,

	output     [31:0] m_nmi_addr,
	output     [31:0] m_nmi_wdata,
	output     [ 3:0] m_nmi_wstrb,
	input      [31:0] m_nmi_rdata,

	// Look-Ahead Interface
	output            mem_la_read,
	output            mem_la_write,
	output     [31:0] mem_la_addr,
	output reg [31:0] mem_la_wdata,
	output reg [ 3:0] mem_la_wstrb,

	// Pico Co-Processor Interface (PCPI)
	output reg        pcpi_valid,
	output reg [31:0] pcpi_insn,
	output     [31:0] pcpi_rs1,
	output     [31:0] pcpi_rs2,
	input             pcpi_wr,
	input      [31:0] pcpi_rd,
	input             pcpi_wait,
	input             pcpi_ready,

	// IRQ Interface
	input      [31:0] irq,
	output     [31:0] eoi,

	// Trace Interface
	output            trace_valid,
	output     [35:0] trace_data,

	// SEU counter enable
	output reg        seu_o
);

	// -----------------------------------
	// Output voting
	reg trap_int;
	wire trap_intVoted = trap_int;
	assign trap = trap_intVoted;

	reg mem_valid_int;
	wire mem_valid_intVoted = mem_valid_int;
	assign m_nmi_valid = mem_valid_intVoted;

	reg mem_instr_int;
	wire mem_instr_intVoted = mem_instr_int;
	assign m_nmi_instr = mem_instr_intVoted;

	reg [31:0] mem_addr_int;
	wire [31:0] mem_addr_intVoted = mem_addr_int;
	assign m_nmi_addr = mem_addr_intVoted;

	reg [31:0] mem_wdata_int;
	wire [31:0] mem_wdata_intVoted = mem_wdata_int;
	assign m_nmi_wdata = mem_wdata_intVoted;

	reg [3:0] mem_wstrb_int;
	wire [3:0] mem_wstrb_intVoted = mem_wstrb_int;
	assign m_nmi_wstrb = mem_wstrb_intVoted;

	reg [31:0] eoi_int;
	wire [31:0] eoi_intVoted = eoi_int;
	assign eoi = eoi_intVoted;

	reg trace_valid_int;
	wire trace_valid_intVoted = trace_valid_int;
	assign trace_valid = trace_valid_intVoted;

	reg [35:0] trace_data_int;
	wire [35:0] trace_data_intVoted = trace_data_int;
	assign trace_data = trace_data_intVoted;
	// -----------------------------------

	// SEU counter enable generation
	wire tmrError = 1'b0;

	always @(posedge clk) begin
		if (!rstn) seu_o <= 1'b0;
		else seu_o <= tmrError;
	end

	localparam irq_timer = 0;
	localparam irq_ebreak = 1;
	localparam irq_buserror = 2;

	localparam irqregs_offset = ENABLE_REGS_16_31 ? 32 : 16;
	localparam cpuregfile_size = (ENABLE_REGS_16_31 ? 32 : 16) + 4*ENABLE_IRQ*ENABLE_IRQ_QREGS;
	localparam cpuregindex_bits = (ENABLE_REGS_16_31 ? 5 : 4) + ENABLE_IRQ*ENABLE_IRQ_QREGS;

	localparam WITH_PCPI = ENABLE_PCPI || ENABLE_MUL || ENABLE_FAST_MUL || ENABLE_DIV;

	localparam [35:0] TRACE_BRANCH = {4'b 0001, 32'b 0};
	localparam [35:0] TRACE_ADDR   = {4'b 0010, 32'b 0};
	localparam [35:0] TRACE_IRQ    = {4'b 1000, 32'b 0};

	reg [63:0] count_cycle, count_instr;
	wire [63:0] count_cycleVoted = count_cycle;
	wire [63:0] count_instrVoted = count_instr;

	reg [31:0] reg_pc, reg_next_pc, reg_op1, reg_op2, reg_out;
	wire [31:0] reg_pcVoted = reg_pc;
	wire [31:0] reg_next_pcVoted = reg_next_pc;
	wire [31:0] reg_op1Voted = reg_op1;
	wire [31:0] reg_op2Voted = reg_op2;
	wire [31:0] reg_outVoted = reg_out;

	reg [4:0] reg_sh;
	wire [4:0] reg_shVoted = reg_sh;

	reg [31:0] next_insn_opcode;
	reg [31:0] dbg_insn_opcode;
	reg [31:0] dbg_insn_addr;

	wire dbg_mem_valid = mem_valid_intVoted;
	wire dbg_mem_instr = mem_instr_intVoted;
	wire dbg_mem_ready = m_nmi_ready;
	wire [31:0] dbg_mem_addr  = mem_addr_intVoted;
	wire [31:0] dbg_mem_wdata = mem_wdata_intVoted;
	wire [ 3:0] dbg_mem_wstrb = mem_wstrb_intVoted;
	wire [31:0] dbg_mem_rdata = m_nmi_rdata;

	assign pcpi_rs1 = reg_op1Voted;
	assign pcpi_rs2 = reg_op2Voted;

	wire [31:0] next_pc;

	reg irq_delay;
	wire irq_delayVoted = irq_delay;
	reg irq_active;
	wire irq_activeVoted = irq_active;
	reg [31:0] irq_mask;
	wire [31:0] irq_maskVoted = irq_mask;
	reg [31:0] irq_pending;
	wire [31:0] irq_pendingVoted = irq_pending;
	reg [31:0] timer;
	wire [31:0] timerVoted = timer;

	reg [31:0] cpuregs [0:cpuregfile_size-1];
	wire [31:0] cpuregsVoted [0:cpuregfile_size-1];
	genvar i;
	generate
		for (i = 0; i < cpuregfile_size; i = i+1) begin
			assign cpuregsVoted[i] = cpuregs[i];
		end
	endgenerate

    // Public signals for debugging
    reg [31:0] x0_reg, x1_reg, x2_reg, x3_reg, x4_reg, x5_reg, x6_reg, x7_reg, x8_reg, x9_reg, x10_reg, x11_reg, x12_reg, x13_reg, x14_reg, x15_reg, x16_reg, x17_reg, x18_reg, x19_reg, x20_reg, x21_reg, x22_reg, x23_reg, x24_reg, x25_reg, x26_reg, x27_reg, x28_reg, x29_reg, x30_reg, x31_reg;
    assign x0_reg = cpuregs[0];
    assign x1_reg = cpuregs[1];
    assign x2_reg = cpuregs[2];
    assign x3_reg = cpuregs[3];
    assign x4_reg = cpuregs[4];
    assign x5_reg = cpuregs[5];
    assign x6_reg = cpuregs[6];
    assign x7_reg = cpuregs[7];
    assign x8_reg = cpuregs[8];
    assign x9_reg = cpuregs[9];
    assign x10_reg = cpuregs[10];
    assign x11_reg = cpuregs[11];
    assign x12_reg = cpuregs[12];
    assign x13_reg = cpuregs[13];
    assign x14_reg = cpuregs[14];
    assign x15_reg = cpuregs[15];
    assign x16_reg = cpuregs[16];
    assign x17_reg = cpuregs[17];
    assign x18_reg = cpuregs[18];
    assign x19_reg = cpuregs[19];
    assign x20_reg = cpuregs[20];
    assign x21_reg = cpuregs[21];
    assign x22_reg = cpuregs[22];
    assign x23_reg = cpuregs[23];
    assign x24_reg = cpuregs[24];
    assign x25_reg = cpuregs[25];
    assign x26_reg = cpuregs[26];
    assign x27_reg = cpuregs[27];
    assign x28_reg = cpuregs[28];
    assign x29_reg = cpuregs[29];
    assign x30_reg = cpuregs[30];
    assign x31_reg = cpuregs[31];

	integer j;
	initial begin
		if (REGS_INIT_ZERO) begin
			for (j = 0; j < cpuregfile_size; j = j+1)
				cpuregs[j] = 0;
		end
	end

	// Internal PCPI Cores

	wire        pcpi_mul_wr;
	wire [31:0] pcpi_mul_rd;
	wire        pcpi_mul_wait;
	wire        pcpi_mul_ready;

	wire        pcpi_div_wr;
	wire [31:0] pcpi_div_rd;
	wire        pcpi_div_wait;
	wire        pcpi_div_ready;

	reg        pcpi_int_wr;
	reg [31:0] pcpi_int_rd;
	reg        pcpi_int_wait;
	reg        pcpi_int_ready;

	// generate if (ENABLE_FAST_MUL) begin
		// picorv32_pcpi_fast_mul pcpi_mul (
		// 	.clk       (clk            ),
		// 	.rstn    (rstn         ),
		// 	.pcpi_valid(pcpi_valid     ),
		// 	.pcpi_insn (pcpi_insn     ),
		// 	.pcpi_rs1  (pcpi_rs1       ),
		// 	.pcpi_rs2  (pcpi_rs2       ),
		// 	.pcpi_wr   (pcpi_mul_wr    ),
		// 	.pcpi_rd   (pcpi_mul_rd    ),
		// 	.pcpi_wait (pcpi_mul_wait  ),
		// 	.pcpi_ready(pcpi_mul_ready )
		// );
	// end else if (ENABLE_MUL) begin
		// picorv32_pcpi_mul pcpi_mul (
		// 	.clk       (clk            ),
		// 	.rstn    (rstn         ),
		// 	.pcpi_valid(pcpi_valid     ),
		// 	.pcpi_insn (pcpi_insn      ),
		// 	.pcpi_rs1  (pcpi_rs1       ),
		// 	.pcpi_rs2  (pcpi_rs2       ),
		// 	.pcpi_wr   (pcpi_mul_wr    ),
		// 	.pcpi_rd   (pcpi_mul_rd    ),
		// 	.pcpi_wait (pcpi_mul_wait  ),
		// 	.pcpi_ready(pcpi_mul_ready )
		// );
	// end else begin
		assign pcpi_mul_wr = 0;
		assign pcpi_mul_rd = 32'bx;
		assign pcpi_mul_wait = 0;
		assign pcpi_mul_ready = 0;
	// end endgenerate

	// generate if (ENABLE_DIV) begin
		// picorv32_pcpi_div pcpi_div (
		// 	.clk       (clk            ),
		// 	.rstn    (rstn         ),
		// 	.pcpi_valid(pcpi_valid     ),
		// 	.pcpi_insn (pcpi_insn      ),
		// 	.pcpi_rs1  (pcpi_rs1       ),
		// 	.pcpi_rs2  (pcpi_rs2       ),
		// 	.pcpi_wr   (pcpi_div_wr    ),
		// 	.pcpi_rd   (pcpi_div_rd    ),
		// 	.pcpi_wait (pcpi_div_wait  ),
		// 	.pcpi_ready(pcpi_div_ready )
		// );
	// end else begin
		assign pcpi_div_wr = 0;
		assign pcpi_div_rd = 32'bx;
		assign pcpi_div_wait = 0;
		assign pcpi_div_ready = 0;
	// end endgenerate

	always @* begin
		pcpi_int_wr = 0;
		pcpi_int_rd = 32'bx;
		pcpi_int_wait  = |{ENABLE_PCPI && pcpi_wait,  (ENABLE_MUL || ENABLE_FAST_MUL) && pcpi_mul_wait,  ENABLE_DIV && pcpi_div_wait};
		pcpi_int_ready = |{ENABLE_PCPI && pcpi_ready, (ENABLE_MUL || ENABLE_FAST_MUL) && pcpi_mul_ready, ENABLE_DIV && pcpi_div_ready};

		(* parallel_case *)
		case (1'b1)
			ENABLE_PCPI && pcpi_ready: begin
				pcpi_int_wr = ENABLE_PCPI ? pcpi_wr : 0;
				pcpi_int_rd = ENABLE_PCPI ? pcpi_rd : 0;
			end
			(ENABLE_MUL || ENABLE_FAST_MUL) && pcpi_mul_ready: begin
				pcpi_int_wr = pcpi_mul_wr;
				pcpi_int_rd = pcpi_mul_rd;
			end
			ENABLE_DIV && pcpi_div_ready: begin
				pcpi_int_wr = pcpi_div_wr;
				pcpi_int_rd = pcpi_div_rd;
			end
		endcase
	end


	// Memory Interface

	reg [1:0] mem_state;
	wire [1:0] mem_stateVoted = mem_state;
	reg [1:0] mem_wordsize;
	wire [1:0] mem_wordsizeVoted = mem_wordsize;
	reg [31:0] mem_rdata_word;
	reg [31:0] mem_rdata_q;
	wire [31:0] mem_rdata_qVoted = mem_rdata_q;
	reg mem_do_prefetch;
	wire mem_do_prefetchVoted = mem_do_prefetch;
	reg mem_do_rinst;
	wire mem_do_rinstVoted = mem_do_rinst;
	reg mem_do_rdata;
	wire mem_do_rdataVoted = mem_do_rdata;
	reg mem_do_wdata;
	wire mem_do_wdataVoted = mem_do_wdata;

	wire mem_xfer;
	reg mem_la_secondword, mem_la_firstword_reg, last_mem_valid;
	wire mem_la_secondwordVoted = mem_la_secondword;
	wire mem_la_firstword_regVoted = mem_la_firstword_reg;
	wire last_mem_validVoted = last_mem_valid;

	wire mem_la_firstword = COMPRESSED_ISA && (mem_do_prefetchVoted || mem_do_rinstVoted) && next_pc[1] && (!mem_la_secondwordVoted);
	wire mem_la_firstword_xfer = COMPRESSED_ISA && mem_xfer && (!last_mem_validVoted ? mem_la_firstword : mem_la_firstword_regVoted);

	reg prefetched_high_word;
	wire prefetched_high_wordVoted = prefetched_high_word;
	reg clear_prefetched_high_word;
	reg [15:0] mem_16bit_buffer;
	wire [15:0] mem_16bit_bufferVoted = mem_16bit_buffer;

	wire [31:0] mem_rdata_latched_noshuffle;
	wire [31:0] mem_rdata_latched;

	wire mem_la_use_prefetched_high_word = COMPRESSED_ISA && mem_la_firstword && prefetched_high_wordVoted && (!clear_prefetched_high_word);
	assign mem_xfer = (mem_valid_intVoted && m_nmi_ready) || (mem_la_use_prefetched_high_word && mem_do_rinstVoted);

	wire mem_busy = |{mem_do_prefetchVoted, mem_do_rinstVoted, mem_do_rdataVoted, mem_do_wdataVoted};
	wire mem_done = rstn && ((mem_xfer && (|mem_stateVoted) && (mem_do_rinstVoted || mem_do_rdataVoted || mem_do_wdataVoted)) || (&mem_stateVoted && mem_do_rinstVoted)) &&
			(!mem_la_firstword || (~&mem_rdata_latched[1:0] && mem_xfer));

	assign mem_la_write = rstn && (!mem_stateVoted) && mem_do_wdataVoted;
	assign mem_la_read = rstn && ((!mem_la_use_prefetched_high_word && (!mem_stateVoted) && (mem_do_rinstVoted || mem_do_prefetchVoted || mem_do_rdataVoted)) ||
			(COMPRESSED_ISA && mem_xfer && (!last_mem_validVoted ? mem_la_firstword : mem_la_firstword_regVoted) && (!mem_la_secondwordVoted) && (&mem_rdata_latched[1:0])));
	assign mem_la_addr = (mem_do_prefetchVoted || mem_do_rinstVoted) ? {next_pc[31:2] + mem_la_firstword_xfer, 2'b00} : {reg_op1Voted[31:2], 2'b00};

	assign mem_rdata_latched_noshuffle = (mem_xfer || LATCHED_MEM_RDATA) ? m_nmi_rdata : mem_rdata_qVoted;

	assign mem_rdata_latched = COMPRESSED_ISA && mem_la_use_prefetched_high_word ? {16'bx, mem_16bit_bufferVoted} :
			COMPRESSED_ISA && mem_la_secondwordVoted ? {mem_rdata_latched_noshuffle[15:0], mem_16bit_bufferVoted} :
			COMPRESSED_ISA && mem_la_firstword ? {16'bx, mem_rdata_latched_noshuffle[31:16]} : mem_rdata_latched_noshuffle;

	always @(posedge clk) begin
		mem_la_firstword_reg 	<= mem_la_firstword_regVoted;
		last_mem_valid 			<= last_mem_validVoted;
		if (!rstn) begin
			mem_la_firstword_reg <= 0;
			last_mem_valid <= 0;
		end else begin
			if (!last_mem_validVoted)
				mem_la_firstword_reg <= mem_la_firstword;
			last_mem_valid <= mem_valid_intVoted && (!m_nmi_ready);
		end
	end

	// Handle load and store
	// mem_wordsize = 0: word load/store
	// mem_wordsize = 1: halfword load/store, select upper/lower 16 bits based on reg_op1[1]
	// mem_wordsize = 2: byte load/store, select correct byte based on reg_op1[1:0]
	always @* begin
		(* full_case *)
		case (mem_wordsizeVoted)
			0: begin
				mem_la_wdata = reg_op2Voted;
				mem_la_wstrb = 4'b1111;
				mem_rdata_word = m_nmi_rdata;
			end
			1: begin
				mem_la_wdata = {2{reg_op2Voted[15:0]}};
				mem_la_wstrb = reg_op1Voted[1] ? 4'b1100 : 4'b0011;
				case (reg_op1Voted[1])
					1'b0: mem_rdata_word = {16'b0, m_nmi_rdata[15: 0]};
					1'b1: mem_rdata_word = {16'b0, m_nmi_rdata[31:16]};
				endcase
			end
			2: begin
				mem_la_wdata = {4{reg_op2Voted[7:0]}};
				mem_la_wstrb = 4'b0001 << reg_op1Voted[1:0];
				case (reg_op1Voted[1:0])
					2'b00: mem_rdata_word = {24'b0, m_nmi_rdata[ 7: 0]};
					2'b01: mem_rdata_word = {24'b0, m_nmi_rdata[15: 8]};
					2'b10: mem_rdata_word = {24'b0, m_nmi_rdata[23:16]};
					2'b11: mem_rdata_word = {24'b0, m_nmi_rdata[31:24]};
				endcase
			end
		endcase
	end

	reg [11:0] mem_rdata_q_temp;

	always @(posedge clk) begin
		mem_rdata_q 		<= mem_rdata_qVoted;

		if (mem_xfer) begin
			mem_rdata_q <= COMPRESSED_ISA ? mem_rdata_latched : m_nmi_rdata;
			next_insn_opcode <= COMPRESSED_ISA ? mem_rdata_latched : m_nmi_rdata;
		end

		// Expand compressed instructions
		if (COMPRESSED_ISA && mem_done && (mem_do_prefetchVoted || mem_do_rinstVoted)) begin
			case (mem_rdata_latched[1:0])
				2'b00: begin // Quadrant 0
					case (mem_rdata_latched[15:13])
						3'b000: begin // C.ADDI4SPN
							mem_rdata_q[14:12] <= 3'b000;
							mem_rdata_q[31:20] <= {2'b0, mem_rdata_latched[10:7], mem_rdata_latched[12:11], mem_rdata_latched[5], mem_rdata_latched[6], 2'b00};
						end
						3'b010: begin // C.LW
							mem_rdata_q[31:20] <= {5'b0, mem_rdata_latched[5], mem_rdata_latched[12:10], mem_rdata_latched[6], 2'b00};
							mem_rdata_q[14:12] <= 3'b 010;
						end
						3'b 110: begin // C.SW
							mem_rdata_q_temp = {5'b0, mem_rdata_latched[5], mem_rdata_latched[12:10], mem_rdata_latched[6], 2'b00};
							mem_rdata_q[31:25] <= mem_rdata_q_temp[11:5];
							mem_rdata_q[11:7]  <= mem_rdata_q_temp[4:0];
							mem_rdata_q[14:12] <= 3'b 010;
						end
					endcase
				end
				2'b01: begin // Quadrant 1
					case (mem_rdata_latched[15:13])
						3'b 000: begin // C.ADDI
							mem_rdata_q[14:12] <= 3'b000;
							mem_rdata_q[31:20] <= $signed({mem_rdata_latched[12], mem_rdata_latched[6:2]});
						end
						3'b 010: begin // C.LI
							mem_rdata_q[14:12] <= 3'b000;
							mem_rdata_q[31:20] <= $signed({mem_rdata_latched[12], mem_rdata_latched[6:2]});
						end
						3'b 011: begin
							if (mem_rdata_latched[11:7] == 2) begin // C.ADDI16SP
								mem_rdata_q[14:12] <= 3'b000;
								mem_rdata_q[31:20] <= $signed({mem_rdata_latched[12], mem_rdata_latched[4:3],
										mem_rdata_latched[5], mem_rdata_latched[2], mem_rdata_latched[6], 4'b 0000});
							end else begin // C.LUI
								mem_rdata_q[31:12] <= $signed({mem_rdata_latched[12], mem_rdata_latched[6:2]});
							end
						end
						3'b100: begin
							if (mem_rdata_latched[11:10] == 2'b00) begin // C.SRLI
								mem_rdata_q[31:25] <= 7'b0000000;
								mem_rdata_q[14:12] <= 3'b 101;
							end
							if (mem_rdata_latched[11:10] == 2'b01) begin // C.SRAI
								mem_rdata_q[31:25] <= 7'b0100000;
								mem_rdata_q[14:12] <= 3'b 101;
							end
							if (mem_rdata_latched[11:10] == 2'b10) begin // C.ANDI
								mem_rdata_q[14:12] <= 3'b111;
								mem_rdata_q[31:20] <= $signed({mem_rdata_latched[12], mem_rdata_latched[6:2]});
							end
							if (mem_rdata_latched[12:10] == 3'b011) begin // C.SUB, C.XOR, C.OR, C.AND
								if (mem_rdata_latched[6:5] == 2'b00) mem_rdata_q[14:12] <= 3'b000;
								if (mem_rdata_latched[6:5] == 2'b01) mem_rdata_q[14:12] <= 3'b100;
								if (mem_rdata_latched[6:5] == 2'b10) mem_rdata_q[14:12] <= 3'b110;
								if (mem_rdata_latched[6:5] == 2'b11) mem_rdata_q[14:12] <= 3'b111;
								mem_rdata_q[31:25] <= mem_rdata_latched[6:5] == 2'b00 ? 7'b0100000 : 7'b0000000;
							end
						end
						3'b 110: begin // C.BEQZ
							mem_rdata_q[14:12] <= 3'b000;
							mem_rdata_q_temp = $signed({mem_rdata_latched[12], mem_rdata_latched[6:5], mem_rdata_latched[2], mem_rdata_latched[11:10], mem_rdata_latched[4:3]});
							mem_rdata_q[31]    <= mem_rdata_q_temp[11];
							mem_rdata_q[7]	   <= mem_rdata_q_temp[10];
							mem_rdata_q[30:25] <= mem_rdata_q_temp[9:4];
							mem_rdata_q[11:8]  <= mem_rdata_q_temp[3:0];
						end
						3'b 111: begin // C.BNEZ
							mem_rdata_q[14:12] <= 3'b001;
							mem_rdata_q_temp = $signed({mem_rdata_latched[12], mem_rdata_latched[6:5], mem_rdata_latched[2], mem_rdata_latched[11:10], mem_rdata_latched[4:3]});
							mem_rdata_q[31]    <= mem_rdata_q_temp[11];
							mem_rdata_q[7]	   <= mem_rdata_q_temp[10];
							mem_rdata_q[30:25] <= mem_rdata_q_temp[9:4];
							mem_rdata_q[11:8]  <= mem_rdata_q_temp[3:0];
						end
					endcase
				end
				2'b10: begin // Quadrant 2
					case (mem_rdata_latched[15:13])
						3'b000: begin // C.SLLI
							mem_rdata_q[31:25] <= 7'b0000000;
							mem_rdata_q[14:12] <= 3'b 001;
						end
						3'b010: begin // C.LWSP
							mem_rdata_q[31:20] <= {4'b0, mem_rdata_latched[3:2], mem_rdata_latched[12], mem_rdata_latched[6:4], 2'b00};
							mem_rdata_q[14:12] <= 3'b 010;
						end
						3'b100: begin
							if (mem_rdata_latched[12] == 0 && mem_rdata_latched[6:2] == 0) begin // C.JR
								mem_rdata_q[14:12] <= 3'b000;
								mem_rdata_q[31:20] <= 12'b0;
							end
							if (mem_rdata_latched[12] == 0 && mem_rdata_latched[6:2] != 0) begin // C.MV
								mem_rdata_q[14:12] <= 3'b000;
								mem_rdata_q[31:25] <= 7'b0000000;
							end
							if (mem_rdata_latched[12] != 0 && mem_rdata_latched[11:7] != 0 && mem_rdata_latched[6:2] == 0) begin // C.JALR
								mem_rdata_q[14:12] <= 3'b000;
								mem_rdata_q[31:20] <= 12'b0;
							end
							if (mem_rdata_latched[12] != 0 && mem_rdata_latched[6:2] != 0) begin // C.ADD
								mem_rdata_q[14:12] <= 3'b000;
								mem_rdata_q[31:25] <= 7'b0000000;
							end
						end
						3'b110: begin // C.SWSP
							mem_rdata_q_temp =  {4'b0, mem_rdata_latched[8:7], mem_rdata_latched[12:9], 2'b00};
							mem_rdata_q[31:25] <= mem_rdata_q_temp[11:5];
							mem_rdata_q[11:7]  <= mem_rdata_q_temp[4:0];
							mem_rdata_q[14:12] <= 3'b 010;
						end
					endcase
				end
			endcase
		end
	end

	// always @(posedge clk) begin
	// 	if (rstn && !trap_intVoted) begin
	// 		if (mem_do_prefetchVoted || mem_do_rinstVoted || mem_do_rdataVoted)
	// 			`assert(!mem_do_wdataVoted);

	// 		if (mem_do_prefetchVoted || mem_do_rinstVoted)
	// 			`assert(!mem_do_rdataVoted);

	// 		if (mem_do_rdataVoted)
	// 			`assert(!mem_do_prefetchVoted && !mem_do_rinstVoted);

	// 		if (mem_do_wdataVoted)
	// 			`assert(!(mem_do_prefetchVoted || mem_do_rinstVoted || mem_do_rdataVoted));

	// 		if (mem_state == 2 || mem_state == 3)
	// 			`assert(mem_valid_intVoted || mem_do_prefetchVoted);
	// 	end
	// end

	always @(posedge clk) begin
		mem_state 				<= mem_stateVoted;
		mem_valid_int 			<= mem_valid_intVoted;
		mem_la_secondword 		<= mem_la_secondwordVoted;
		prefetched_high_word	<= prefetched_high_wordVoted;
		mem_addr_int 			<= mem_addr_intVoted;
		mem_wstrb_int 			<= mem_wstrb_intVoted;
		mem_wdata_int			<= mem_wdata_intVoted;
		mem_instr_int			<= mem_instr_intVoted;
		mem_16bit_buffer 		<= mem_16bit_bufferVoted;

		if (!rstn || trap_intVoted) begin
			if (!rstn)
				mem_state <= 0;
			if (!rstn || m_nmi_ready)
				mem_valid_int <= 0;
			mem_la_secondword <= 0;
			prefetched_high_word <= 0;
		end else begin
			if (mem_la_read || mem_la_write) begin
				mem_addr_int <= mem_la_addr;
				mem_wstrb_int <= mem_la_wstrb & {4{mem_la_write}};
			end
			if (mem_la_write) begin
				mem_wdata_int <= mem_la_wdata;
			end
			case (mem_stateVoted)
				0: begin
					if (mem_do_prefetchVoted || mem_do_rinstVoted || mem_do_rdataVoted) begin
						mem_valid_int <= !mem_la_use_prefetched_high_word;
						mem_instr_int <= mem_do_prefetchVoted || mem_do_rinstVoted;
						mem_wstrb_int <= 0;
						mem_state <= 1;
					end
					if (mem_do_wdataVoted) begin
						mem_valid_int <= 1;
						mem_instr_int <= 0;
						mem_state <= 2;
					end
				end
				1: begin
					// `assert(mem_wstrb_intVoted == 0);
					// `assert(mem_do_prefetchVoted || mem_do_rinstVoted || mem_do_rdataVoted);
					// `assert(mem_valid_intVoted == !mem_la_use_prefetched_high_word);
					// `assert(mem_instr_intVoted == (mem_do_prefetchVoted || mem_do_rinstVoted));
					if (mem_xfer) begin
						if (COMPRESSED_ISA && mem_la_read) begin
							mem_valid_int <= 1;
							mem_la_secondword <= 1;
							if (!mem_la_use_prefetched_high_word)
								mem_16bit_buffer <= m_nmi_rdata[31:16];
						end else begin
							mem_valid_int <= 0;
							mem_la_secondword <= 0;
							if (COMPRESSED_ISA && (!mem_do_rdataVoted)) begin
								if (~&m_nmi_rdata[1:0] || mem_la_secondwordVoted) begin
									mem_16bit_buffer <= m_nmi_rdata[31:16];
									prefetched_high_word <= 1;
								end else begin
									prefetched_high_word <= 0;
								end
							end
							mem_state <= mem_do_rinstVoted || mem_do_rdataVoted ? 0 : 3;
						end
					end
				end
				2: begin
					// `assert(mem_wstrb_intVoted != 0);
					// `assert(mem_do_wdataVoted);
					if (mem_xfer) begin
						mem_valid_int <= 0;
						mem_state <= 0;
					end
				end
				3: begin
					// `assert(mem_wstrb_intVoted == 0);
					// `assert(mem_do_prefetchVoted);
					if (mem_do_rinstVoted) begin
						mem_state <= 0;
					end
				end
			endcase
		end

		if (clear_prefetched_high_word)
			prefetched_high_word <= 0;
	end


	// Instruction Decoder

	reg instr_lui, instr_auipc, instr_jal, instr_jalr;
	wire instr_luiVoted = instr_lui;
	wire instr_auipcVoted = instr_auipc;
	wire instr_jalVoted = instr_jal;
	wire instr_jalrVoted = instr_jalr;

	reg instr_beq, instr_bne, instr_blt, instr_bge, instr_bltu, instr_bgeu;
	wire instr_beqVoted = instr_beq;
	wire instr_bneVoted = instr_bne;
	wire instr_bltVoted = instr_blt;
	wire instr_bgeVoted = instr_bge;
	wire instr_bltuVoted = instr_bltu;
	wire instr_bgeuVoted = instr_bgeu;

	reg instr_lb, instr_lh, instr_lw, instr_lbu, instr_lhu, instr_sb, instr_sh, instr_sw;
	wire instr_lbVoted = instr_lb;
	wire instr_lhVoted = instr_lh;
	wire instr_lwVoted = instr_lw;
	wire instr_lbuVoted = instr_lbu;
	wire instr_lhuVoted = instr_lhu;
	wire instr_sbVoted = instr_sb;
	wire instr_shVoted = instr_sh;
	wire instr_swVoted = instr_sw;

	reg instr_addi, instr_slti, instr_sltiu, instr_xori, instr_ori, instr_andi, instr_slli, instr_srli, instr_srai;
	wire instr_addiVoted = instr_addi;
	wire instr_sltiVoted = instr_slti;
	wire instr_sltiuVoted = instr_sltiu;
	wire instr_xoriVoted = instr_xori;
	wire instr_oriVoted = instr_ori;
	wire instr_andiVoted = instr_andi;
	wire instr_slliVoted = instr_slli;
	wire instr_srliVoted = instr_srli;
	wire instr_sraiVoted = instr_srai;

	reg instr_add, instr_sub, instr_sll, instr_slt, instr_sltu, instr_xor, instr_srl, instr_sra, instr_or, instr_and;
	wire instr_addVoted = instr_add;
	wire instr_subVoted = instr_sub;
	wire instr_sllVoted = instr_sll;
	wire instr_sltVoted = instr_slt;
	wire instr_sltuVoted = instr_sltu;
	wire instr_xorVoted = instr_xor;
	wire instr_srlVoted = instr_srl;
	wire instr_sraVoted = instr_sra;
	wire instr_orVoted = instr_or;
	wire instr_andVoted = instr_and;
	
	reg instr_rdcycle, instr_rdcycleh, instr_rdinstr, instr_rdinstrh, instr_ecall_ebreak;
	wire instr_rdcycleVoted = instr_rdcycle;
	wire instr_rdcyclehVoted = instr_rdcycleh;
	wire instr_rdinstrVoted = instr_rdinstr;
	wire instr_rdinstrhVoted = instr_rdinstrh;

	reg instr_getq, instr_setq, instr_retirq, instr_maskirq, instr_waitirq, instr_timer;
	wire instr_getqVoted = instr_getq;
	wire instr_setqVoted = instr_setq;
	wire instr_retirqVoted = instr_retirq;
	wire instr_maskirqVoted = instr_maskirq;
	wire instr_waitirqVoted = instr_waitirq;
	wire instr_timerVoted = instr_timer;

	wire instr_trap;

	reg [cpuregindex_bits-1:0] decoded_rd, decoded_rs1, decoded_rs2;
	wire [cpuregindex_bits-1:0] decoded_rdVoted = decoded_rd;
	wire [cpuregindex_bits-1:0] decoded_rs1Voted = decoded_rs1;
	wire [cpuregindex_bits-1:0] decoded_rs2Voted = decoded_rs2;

	reg [31:0] decoded_imm, decoded_imm_j;
	wire [31:0] decoded_imm_jVoted = decoded_imm_j;
	wire [31:0] decoded_immVoted = decoded_imm;

	reg decoder_trigger;
	wire decoder_triggerVoted = decoder_trigger;
	reg decoder_trigger_q;
	reg decoder_pseudo_trigger;
	wire decoder_pseudo_triggerVoted = decoder_pseudo_trigger;
	reg decoder_pseudo_trigger_q;
	reg compressed_instr;
	wire compressed_instrVoted = compressed_instr;

	reg is_lui_auipc_jal;
	wire is_lui_auipc_jalVoted = is_lui_auipc_jal;
	reg is_lb_lh_lw_lbu_lhu;
	wire is_lb_lh_lw_lbu_lhuVoted = is_lb_lh_lw_lbu_lhu;
	reg is_slli_srli_srai;
	wire is_slli_srli_sraiVoted = is_slli_srli_srai;
	reg is_jalr_addi_slti_sltiu_xori_ori_andi;
	wire is_jalr_addi_slti_sltiu_xori_ori_andiVoted = is_jalr_addi_slti_sltiu_xori_ori_andi;
	reg is_sb_sh_sw;
	wire is_sb_sh_swVoted = is_sb_sh_sw;
	reg is_sll_srl_sra;
	wire is_sll_srl_sraVoted = is_sll_srl_sra;
	reg is_lui_auipc_jal_jalr_addi_add_sub;
	wire is_lui_auipc_jal_jalr_addi_add_subVoted = is_lui_auipc_jal_jalr_addi_add_sub;
	reg is_slti_blt_slt;
	wire is_slti_blt_sltVoted = is_slti_blt_slt;
	reg is_sltiu_bltu_sltu;
	wire is_sltiu_bltu_sltuVoted = is_sltiu_bltu_sltu;
	reg is_beq_bne_blt_bge_bltu_bgeu;
	wire is_beq_bne_blt_bge_bltu_bgeuVoted = is_beq_bne_blt_bge_bltu_bgeu;
	reg is_lbu_lhu_lw;
	wire is_lbu_lhu_lwVoted = is_lbu_lhu_lw;
	reg is_alu_reg_imm;
	wire is_alu_reg_immVoted = is_alu_reg_imm;
	reg is_alu_reg_reg;
	wire is_alu_reg_regVoted = is_alu_reg_reg;
	reg is_compare;
	wire is_compareVoted = is_compare;

	assign instr_trap = (CATCH_ILLINSN || WITH_PCPI) && (!{instr_luiVoted, instr_auipcVoted, instr_jalVoted, instr_jalrVoted,
			instr_beqVoted, instr_bneVoted, instr_bltVoted, instr_bgeVoted, instr_bltuVoted, instr_bgeuVoted,
			instr_lbVoted, instr_lhVoted, instr_lwVoted, instr_lbuVoted, instr_lhuVoted, instr_sbVoted, instr_shVoted, instr_swVoted,
			instr_addiVoted, instr_sltiVoted, instr_sltiuVoted, instr_xoriVoted, instr_oriVoted, instr_andiVoted, instr_slliVoted, instr_srliVoted, instr_sraiVoted,
			instr_addVoted, instr_subVoted, instr_sllVoted, instr_sltVoted, instr_sltuVoted, instr_xorVoted, instr_srlVoted, instr_sraVoted, instr_orVoted, instr_andVoted,
			instr_rdcycleVoted, instr_rdcyclehVoted, instr_rdinstrVoted, instr_rdinstrhVoted,
			instr_getqVoted, instr_setqVoted, instr_retirqVoted, instr_maskirqVoted, instr_waitirqVoted, instr_timerVoted});

	wire is_rdcycle_rdcycleh_rdinstr_rdinstrh;
	assign is_rdcycle_rdcycleh_rdinstr_rdinstrh = |{instr_rdcycleVoted, instr_rdcyclehVoted, instr_rdinstrVoted, instr_rdinstrhVoted};

	reg [63:0] new_ascii_instr;
	/*`FORMAL_KEEP*/ reg [63:0] dbg_ascii_instr;
	/*`FORMAL_KEEP*/ reg [31:0] dbg_insn_imm;
	/*`FORMAL_KEEP*/ reg [4:0] dbg_insn_rs1;
	/*`FORMAL_KEEP*/ reg [4:0] dbg_insn_rs2;
	/*`FORMAL_KEEP*/ reg [4:0] dbg_insn_rd;
	/*`FORMAL_KEEP*/ reg [31:0] dbg_rs1val;
	/*`FORMAL_KEEP*/ reg [31:0] dbg_rs2val;
	/*`FORMAL_KEEP*/ reg dbg_rs1val_valid;
	/*`FORMAL_KEEP*/ reg dbg_rs2val_valid;

    always @* begin
        new_ascii_instr = {8'd0};

		if (instr_luiVoted)      new_ascii_instr = "lui";
		if (instr_auipcVoted)    new_ascii_instr = "auipc";
		if (instr_jalVoted)      new_ascii_instr = "jal";
		if (instr_jalrVoted)     new_ascii_instr = "jalr";

		if (instr_beqVoted)      new_ascii_instr = "beq";
		if (instr_bneVoted)      new_ascii_instr = "bne";
		if (instr_bltVoted)      new_ascii_instr = "blt";
		if (instr_bgeVoted)      new_ascii_instr = "bge";
		if (instr_bltuVoted)     new_ascii_instr = "bltu";
		if (instr_bgeuVoted)     new_ascii_instr = "bgeu";

		if (instr_lbVoted)       new_ascii_instr = "lb";
		if (instr_lhVoted)       new_ascii_instr = "lh";
		if (instr_lwVoted)       new_ascii_instr = "lw";
		if (instr_lbuVoted)      new_ascii_instr = "lbu";
		if (instr_lhuVoted)      new_ascii_instr = "lhu";
		if (instr_sbVoted)       new_ascii_instr = "sb";
		if (instr_shVoted)       new_ascii_instr = "sh";
		if (instr_swVoted)       new_ascii_instr = "sw";

		if (instr_addiVoted)     new_ascii_instr = "addi";
		if (instr_sltiVoted)     new_ascii_instr = "slti";
		if (instr_sltiuVoted)    new_ascii_instr = "sltiu";
		if (instr_xoriVoted)     new_ascii_instr = "xori";
		if (instr_oriVoted)      new_ascii_instr = "ori";
		if (instr_andiVoted)     new_ascii_instr = "andi";
		if (instr_slliVoted)     new_ascii_instr = "slli";
		if (instr_srliVoted)     new_ascii_instr = "srli";
		if (instr_sraiVoted)     new_ascii_instr = "srai";

		if (instr_addVoted)      new_ascii_instr = "add";
		if (instr_subVoted)      new_ascii_instr = "sub";
		if (instr_sllVoted)      new_ascii_instr = "sll";
		if (instr_sltVoted)      new_ascii_instr = "slt";
		if (instr_sltuVoted)     new_ascii_instr = "sltu";
		if (instr_xorVoted)      new_ascii_instr = "xor";
		if (instr_srlVoted)      new_ascii_instr = "srl";
		if (instr_sraVoted)      new_ascii_instr = "sra";
		if (instr_orVoted)       new_ascii_instr = "or";
		if (instr_andVoted)      new_ascii_instr = "and";

		if (instr_rdcycleVoted)  new_ascii_instr = "rdcycle";
		if (instr_rdcyclehVoted) new_ascii_instr = "rdcycleh";
		if (instr_rdinstrVoted)  new_ascii_instr = "rdinstr";
		if (instr_rdinstrhVoted) new_ascii_instr = "rdinstrh";

		if (instr_getqVoted)     new_ascii_instr = "getq";
		if (instr_setqVoted)     new_ascii_instr = "setq";
		if (instr_retirqVoted)   new_ascii_instr = "retirq";
		if (instr_maskirqVoted)  new_ascii_instr = "maskirq";
		if (instr_waitirqVoted)  new_ascii_instr = "waitirq";
		if (instr_timerVoted)    new_ascii_instr = "timer";
	end

	reg [63:0] q_ascii_instr;
	reg [31:0] q_insn_imm;
	reg [31:0] q_insn_opcode;
	reg [4:0] q_insn_rs1;
	reg [4:0] q_insn_rs2;
	reg [4:0] q_insn_rd;
	reg dbg_next;

	wire launch_next_insn;
	reg dbg_valid_insn;

	reg [63:0] cached_ascii_instr;
	reg [31:0] cached_insn_imm;
	reg [31:0] cached_insn_opcode;
	reg [4:0] cached_insn_rs1;
	reg [4:0] cached_insn_rs2;
	reg [4:0] cached_insn_rd;

	always @(posedge clk) begin
		q_ascii_instr <= dbg_ascii_instr;
		q_insn_imm <= dbg_insn_imm;
		q_insn_opcode <= dbg_insn_opcode;
		q_insn_rs1 <= dbg_insn_rs1;
		q_insn_rs2 <= dbg_insn_rs2;
		q_insn_rd <= dbg_insn_rd;
		dbg_next <= launch_next_insn;

		if (!rstn || trap_intVoted)
			dbg_valid_insn <= 0;
		else if (launch_next_insn)
			dbg_valid_insn <= 1;

		if (decoder_trigger_q) begin
			cached_ascii_instr <= new_ascii_instr;
			cached_insn_imm <= decoded_immVoted;
			if (&next_insn_opcode[1:0])
				cached_insn_opcode <= next_insn_opcode;
			else
				cached_insn_opcode <= {16'b0, next_insn_opcode[15:0]};
			cached_insn_rs1 <= decoded_rs1Voted;
			cached_insn_rs2 <= decoded_rs2Voted;
			cached_insn_rd <= decoded_rdVoted;
		end

		if (launch_next_insn) begin
			dbg_insn_addr <= next_pc;
		end
	end

	always @* begin
		dbg_ascii_instr = q_ascii_instr;
		dbg_insn_imm = q_insn_imm;
		dbg_insn_opcode = q_insn_opcode;
		dbg_insn_rs1 = q_insn_rs1;
		dbg_insn_rs2 = q_insn_rs2;
		dbg_insn_rd = q_insn_rd;

		if (dbg_next) begin
			if (decoder_pseudo_trigger_q) begin
				dbg_ascii_instr = cached_ascii_instr;
				dbg_insn_imm = cached_insn_imm;
				dbg_insn_opcode = cached_insn_opcode;
				dbg_insn_rs1 = cached_insn_rs1;
				dbg_insn_rs2 = cached_insn_rs2;
				dbg_insn_rd = cached_insn_rd;
			end else begin
				dbg_ascii_instr = new_ascii_instr;
				if (&next_insn_opcode[1:0])
					dbg_insn_opcode = next_insn_opcode;
				else
					dbg_insn_opcode = {16'b0, next_insn_opcode[15:0]};
				dbg_insn_imm = decoded_immVoted;
				dbg_insn_rs1 = decoded_rs1Voted;
				dbg_insn_rs2 = decoded_rs2Voted;
				dbg_insn_rd = decoded_rdVoted;
			end
		end
	end

// `ifdef DEBUGASM
// 	always @(posedge clk) begin
// 		if (dbg_next) begin
// 			$display("debugasm %x %x %s", dbg_insn_addr, dbg_insn_opcode, dbg_ascii_instr ? dbg_ascii_instr : "*");
// 			dbg_next2 <= dbg_next;
// 		end
// 	end
// `endif


// `ifdef DEBUG
// 	always @(posedge clk) begin
// 		pippo <= 1'b1;
// 		if (dbg_next) begin
// 			if (&dbg_insn_opcode[1:0])
// 				$display("DECODE: 0x%08x 0x%08x %-0s", dbg_insn_addr, dbg_insn_opcode, dbg_ascii_instr ? dbg_ascii_instr : "UNKNOWN");
// 			else
// 				$display("DECODE: 0x%08x     0x%04x %-0s", dbg_insn_addr, dbg_insn_opcode[15:0], dbg_ascii_instr ? dbg_ascii_instr : "UNKNOWN");
// 		end
// 	end
// `endif

	reg [31:0] decoded_imm_j_temp;

	always @(posedge clk) begin
		is_lui_auipc_jal 						<= is_lui_auipc_jalVoted;
		is_lui_auipc_jal_jalr_addi_add_sub		<= is_lui_auipc_jal_jalr_addi_add_subVoted;
		is_slti_blt_slt							<= is_slti_blt_sltVoted;
		is_sltiu_bltu_sltu						<= is_sltiu_bltu_sltuVoted;
		is_lbu_lhu_lw							<= is_lbu_lhu_lwVoted;
		is_compare								<= is_compareVoted;
		instr_lui								<= instr_luiVoted;
		instr_auipc								<= instr_auipcVoted;
		instr_jal								<= instr_jalVoted;
		instr_jalr								<= instr_jalrVoted;
		instr_retirq							<= instr_retirqVoted;
		instr_waitirq							<= instr_waitirqVoted;
		is_beq_bne_blt_bge_bltu_bgeu			<= is_beq_bne_blt_bge_bltu_bgeuVoted;
		is_lb_lh_lw_lbu_lhu						<= is_lb_lh_lw_lbu_lhuVoted;
		is_sb_sh_sw								<= is_sb_sh_swVoted;
		is_alu_reg_imm							<= is_alu_reg_immVoted;
		is_alu_reg_reg							<= is_alu_reg_regVoted;
		decoded_imm_j							<= decoded_imm_jVoted;
		decoded_rd								<= decoded_rdVoted;
		decoded_rs1								<= decoded_rs1Voted;
		decoded_rs2								<= decoded_rs2Voted;
		compressed_instr						<= compressed_instrVoted;
		instr_beq								<= instr_beqVoted;
		instr_bne								<= instr_bneVoted;
		instr_blt								<= instr_bltVoted;
		instr_bge								<= instr_bgeVoted;
		instr_bltu								<= instr_bltuVoted;
		instr_bgeu								<= instr_bgeuVoted;
		instr_lb								<= instr_lbVoted;
		instr_lh								<= instr_lhVoted;
		instr_lw								<= instr_lwVoted;
		instr_lbu								<= instr_lbuVoted;
		instr_lhu								<= instr_lhuVoted;
		instr_sb								<= instr_sbVoted;
		instr_addi 								<= instr_addiVoted;
		instr_slti 								<= instr_sltiVoted;
		instr_sltiu								<= instr_sltiuVoted;
		instr_xori 								<= instr_xoriVoted;
		instr_ori  								<= instr_oriVoted;
		instr_andi 								<= instr_andiVoted;
		instr_add								<= instr_addVoted;
		instr_sub								<= instr_subVoted;
		instr_sll								<= instr_sllVoted;
		instr_slt								<= instr_sltVoted;
		instr_sltu								<= instr_sltuVoted;
		instr_xor								<= instr_xorVoted;
		instr_srl								<= instr_srlVoted;
		instr_sra								<= instr_sraVoted;
		instr_or								<= instr_orVoted;
		instr_and								<= instr_andVoted;
		instr_rdcycle							<= instr_rdcycleVoted;
		instr_rdcycleh							<= instr_rdcyclehVoted;
		instr_rdinstr							<= instr_rdinstrVoted;
		instr_rdinstrh							<= instr_rdinstrhVoted;
		instr_getq								<= instr_getqVoted;
		instr_setq								<= instr_setqVoted;
		instr_maskirq							<= instr_maskirqVoted;
		instr_timer								<= instr_timerVoted;
		is_slli_srli_srai						<= is_slli_srli_sraiVoted;
		is_jalr_addi_slti_sltiu_xori_ori_andi	<= is_jalr_addi_slti_sltiu_xori_ori_andiVoted;
		is_sll_srl_sra							<= is_sll_srl_sraVoted;

		is_lui_auipc_jal <= |{instr_luiVoted, instr_auipcVoted, instr_jalVoted};
		is_lui_auipc_jal_jalr_addi_add_sub <= |{instr_luiVoted, instr_auipcVoted, instr_jalVoted, instr_jalrVoted, instr_addiVoted, instr_addVoted, instr_subVoted};
		is_slti_blt_slt <= |{instr_sltiVoted, instr_bltVoted, instr_sltVoted};
		is_sltiu_bltu_sltu <= |{instr_sltiuVoted, instr_bltuVoted, instr_sltuVoted};
		is_lbu_lhu_lw <= |{instr_lbuVoted, instr_lhuVoted, instr_lwVoted};
		is_compare <= |{is_beq_bne_blt_bge_bltu_bgeuVoted, instr_sltiVoted, instr_sltVoted, instr_sltiuVoted, instr_sltuVoted};

		if (mem_do_rinstVoted && mem_done) begin
			instr_lui     <= mem_rdata_latched[6:0] == 7'b0110111;
			instr_auipc   <= mem_rdata_latched[6:0] == 7'b0010111;
			instr_jal     <= mem_rdata_latched[6:0] == 7'b1101111;
			instr_jalr    <= mem_rdata_latched[6:0] == 7'b1100111 && mem_rdata_latched[14:12] == 3'b000;
			instr_retirq  <= mem_rdata_latched[6:0] == 7'b0001011 && mem_rdata_latched[31:25] == 7'b0000010 && ENABLE_IRQ;
			instr_waitirq <= mem_rdata_latched[6:0] == 7'b0001011 && mem_rdata_latched[31:25] == 7'b0000100 && ENABLE_IRQ;

			is_beq_bne_blt_bge_bltu_bgeu <= mem_rdata_latched[6:0] == 7'b1100011;
			is_lb_lh_lw_lbu_lhu          <= mem_rdata_latched[6:0] == 7'b0000011;
			is_sb_sh_sw                  <= mem_rdata_latched[6:0] == 7'b0100011;
			is_alu_reg_imm               <= mem_rdata_latched[6:0] == 7'b0010011;
			is_alu_reg_reg               <= mem_rdata_latched[6:0] == 7'b0110011;

			decoded_imm_j_temp = $signed({mem_rdata_latched[31:12], 1'b0});
			decoded_imm_j[31:20] <= decoded_imm_j_temp[31:20];
			decoded_imm_j[10:1]  <= decoded_imm_j_temp[19:10];
			decoded_imm_j[11]    <= decoded_imm_j_temp[9];
			decoded_imm_j[19:12] <= decoded_imm_j_temp[8:1];
			decoded_imm_j[0]     <= decoded_imm_j_temp[0];

			decoded_rd <= mem_rdata_latched[11:7];
			decoded_rs1 <= mem_rdata_latched[19:15];
			decoded_rs2 <= mem_rdata_latched[24:20];

			if (mem_rdata_latched[6:0] == 7'b0001011 && mem_rdata_latched[31:25] == 7'b0000000 && ENABLE_IRQ && ENABLE_IRQ_QREGS)
				decoded_rs1[cpuregindex_bits-1] <= 1; // instr_getq

			if (mem_rdata_latched[6:0] == 7'b0001011 && mem_rdata_latched[31:25] == 7'b0000010 && ENABLE_IRQ)
				decoded_rs1 <= ENABLE_IRQ_QREGS ? irqregs_offset : 3; // instr_retirq

			compressed_instr <= 0;
			if (COMPRESSED_ISA && mem_rdata_latched[1:0] != 2'b11) begin
				compressed_instr <= 1;
				decoded_rd <= 0;
				decoded_rs1 <= 0;
				decoded_rs2 <= 0;

				decoded_imm_j_temp = $signed({mem_rdata_latched[12:2], 1'b0});
				decoded_imm_j[31:11] <= decoded_imm_j_temp[31:11];
				decoded_imm_j[4]     <= decoded_imm_j_temp[10];
				decoded_imm_j[9:8]   <= decoded_imm_j_temp[9:8];
				decoded_imm_j[10]    <= decoded_imm_j_temp[7];
				decoded_imm_j[6]     <= decoded_imm_j_temp[6];
			    decoded_imm_j[7]     <= decoded_imm_j_temp[5];
				decoded_imm_j[3:1]   <= decoded_imm_j_temp[4:2];
				decoded_imm_j[5]     <= decoded_imm_j_temp[1];
				decoded_imm_j[0]     <= decoded_imm_j_temp[0];

				case (mem_rdata_latched[1:0])
					2'b00: begin // Quadrant 0
						case (mem_rdata_latched[15:13])
							3'b000: begin // C.ADDI4SPN
								is_alu_reg_imm <= |mem_rdata_latched[12:5];
								decoded_rs1 <= 2;
								decoded_rd <= 8 + mem_rdata_latched[4:2];
							end
							3'b010: begin // C.LW
								is_lb_lh_lw_lbu_lhu <= 1;
								decoded_rs1 <= 8 + mem_rdata_latched[9:7];
								decoded_rd <= 8 + mem_rdata_latched[4:2];
							end
							3'b110: begin // C.SW
								is_sb_sh_sw <= 1;
								decoded_rs1 <= 8 + mem_rdata_latched[9:7];
								decoded_rs2 <= 8 + mem_rdata_latched[4:2];
							end
						endcase
					end
					2'b01: begin // Quadrant 1
						case (mem_rdata_latched[15:13])
							3'b000: begin // C.NOP / C.ADDI
								is_alu_reg_imm <= 1;
								decoded_rd <= mem_rdata_latched[11:7];
								decoded_rs1 <= mem_rdata_latched[11:7];
							end
							3'b001: begin // C.JAL
								instr_jal <= 1;
								decoded_rd <= 1;
							end
							3'b 010: begin // C.LI
								is_alu_reg_imm <= 1;
								decoded_rd <= mem_rdata_latched[11:7];
								decoded_rs1 <= 0;
							end
							3'b 011: begin
								if (mem_rdata_latched[12] || mem_rdata_latched[6:2]) begin
									if (mem_rdata_latched[11:7] == 2) begin // C.ADDI16SP
										is_alu_reg_imm <= 1;
										decoded_rd <= mem_rdata_latched[11:7];
										decoded_rs1 <= mem_rdata_latched[11:7];
									end else begin // C.LUI
										instr_lui <= 1;
										decoded_rd <= mem_rdata_latched[11:7];
										decoded_rs1 <= 0;
									end
								end
							end
							3'b100: begin
								if (!mem_rdata_latched[11] && (!mem_rdata_latched[12])) begin // C.SRLI, C.SRAI
									is_alu_reg_imm <= 1;
									decoded_rd <= 8 + mem_rdata_latched[9:7];
									decoded_rs1 <= 8 + mem_rdata_latched[9:7];
									decoded_rs2 <= {mem_rdata_latched[12], mem_rdata_latched[6:2]};
								end
								if (mem_rdata_latched[11:10] == 2'b10) begin // C.ANDI
									is_alu_reg_imm <= 1;
									decoded_rd <= 8 + mem_rdata_latched[9:7];
									decoded_rs1 <= 8 + mem_rdata_latched[9:7];
								end
								if (mem_rdata_latched[12:10] == 3'b011) begin // C.SUB, C.XOR, C.OR, C.AND
									is_alu_reg_reg <= 1;
									decoded_rd <= 8 + mem_rdata_latched[9:7];
									decoded_rs1 <= 8 + mem_rdata_latched[9:7];
									decoded_rs2 <= 8 + mem_rdata_latched[4:2];
								end
							end
							3'b101: begin // C.J
								instr_jal <= 1;
							end
							3'b110: begin // C.BEQZ
								is_beq_bne_blt_bge_bltu_bgeu <= 1;
								decoded_rs1 <= 8 + mem_rdata_latched[9:7];
								decoded_rs2 <= 0;
							end
							3'b111: begin // C.BNEZ
								is_beq_bne_blt_bge_bltu_bgeu <= 1;
								decoded_rs1 <= 8 + mem_rdata_latched[9:7];
								decoded_rs2 <= 0;
							end
						endcase
					end
					2'b10: begin // Quadrant 2
						case (mem_rdata_latched[15:13])
							3'b000: begin // C.SLLI
								if (!mem_rdata_latched[12]) begin
									is_alu_reg_imm <= 1;
									decoded_rd <= mem_rdata_latched[11:7];
									decoded_rs1 <= mem_rdata_latched[11:7];
									decoded_rs2 <= {mem_rdata_latched[12], mem_rdata_latched[6:2]};
								end
							end
							3'b010: begin // C.LWSP
								if (mem_rdata_latched[11:7]) begin
									is_lb_lh_lw_lbu_lhu <= 1;
									decoded_rd <= mem_rdata_latched[11:7];
									decoded_rs1 <= 2;
								end
							end
							3'b100: begin
								if (mem_rdata_latched[12] == 0 && mem_rdata_latched[11:7] != 0 && mem_rdata_latched[6:2] == 0) begin // C.JR
									instr_jalr <= 1;
									decoded_rd <= 0;
									decoded_rs1 <= mem_rdata_latched[11:7];
								end
								if (mem_rdata_latched[12] == 0 && mem_rdata_latched[6:2] != 0) begin // C.MV
									is_alu_reg_reg <= 1;
									decoded_rd <= mem_rdata_latched[11:7];
									decoded_rs1 <= 0;
									decoded_rs2 <= mem_rdata_latched[6:2];
								end
								if (mem_rdata_latched[12] != 0 && mem_rdata_latched[11:7] != 0 && mem_rdata_latched[6:2] == 0) begin // C.JALR
									instr_jalr <= 1;
									decoded_rd <= 1;
									decoded_rs1 <= mem_rdata_latched[11:7];
								end
								if (mem_rdata_latched[12] != 0 && mem_rdata_latched[6:2] != 0) begin // C.ADD
									is_alu_reg_reg <= 1;
									decoded_rd <= mem_rdata_latched[11:7];
									decoded_rs1 <= mem_rdata_latched[11:7];
									decoded_rs2 <= mem_rdata_latched[6:2];
								end
							end
							3'b110: begin // C.SWSP
								is_sb_sh_sw <= 1;
								decoded_rs1 <= 2;
								decoded_rs2 <= mem_rdata_latched[6:2];
							end
						endcase
					end
				endcase
			end
		end

		if (decoder_triggerVoted && (!decoder_pseudo_triggerVoted)) begin
			pcpi_insn <= WITH_PCPI ? mem_rdata_qVoted : 'bx;

			instr_beq   <= is_beq_bne_blt_bge_bltu_bgeuVoted && mem_rdata_qVoted[14:12] == 3'b000;
			instr_bne   <= is_beq_bne_blt_bge_bltu_bgeuVoted && mem_rdata_qVoted[14:12] == 3'b001;
			instr_blt   <= is_beq_bne_blt_bge_bltu_bgeuVoted && mem_rdata_qVoted[14:12] == 3'b100;
			instr_bge   <= is_beq_bne_blt_bge_bltu_bgeuVoted && mem_rdata_qVoted[14:12] == 3'b101;
			instr_bltu  <= is_beq_bne_blt_bge_bltu_bgeuVoted && mem_rdata_qVoted[14:12] == 3'b110;
			instr_bgeu  <= is_beq_bne_blt_bge_bltu_bgeuVoted && mem_rdata_qVoted[14:12] == 3'b111;

			instr_lb    <= is_lb_lh_lw_lbu_lhuVoted && mem_rdata_qVoted[14:12] == 3'b000;
			instr_lh    <= is_lb_lh_lw_lbu_lhuVoted && mem_rdata_qVoted[14:12] == 3'b001;
			instr_lw    <= is_lb_lh_lw_lbu_lhuVoted && mem_rdata_qVoted[14:12] == 3'b010;
			instr_lbu   <= is_lb_lh_lw_lbu_lhuVoted && mem_rdata_qVoted[14:12] == 3'b100;
			instr_lhu   <= is_lb_lh_lw_lbu_lhuVoted && mem_rdata_qVoted[14:12] == 3'b101;

			instr_sb    <= is_sb_sh_swVoted && mem_rdata_qVoted[14:12] == 3'b000;
			instr_sh    <= is_sb_sh_swVoted && mem_rdata_qVoted[14:12] == 3'b001;
			instr_sw    <= is_sb_sh_swVoted && mem_rdata_qVoted[14:12] == 3'b010;

			instr_addi  <= is_alu_reg_immVoted && mem_rdata_qVoted[14:12] == 3'b000;
			instr_slti  <= is_alu_reg_immVoted && mem_rdata_qVoted[14:12] == 3'b010;
			instr_sltiu <= is_alu_reg_immVoted && mem_rdata_qVoted[14:12] == 3'b011;
			instr_xori  <= is_alu_reg_immVoted && mem_rdata_qVoted[14:12] == 3'b100;
			instr_ori   <= is_alu_reg_immVoted && mem_rdata_qVoted[14:12] == 3'b110;
			instr_andi  <= is_alu_reg_immVoted && mem_rdata_qVoted[14:12] == 3'b111;

			instr_slli  <= is_alu_reg_immVoted && mem_rdata_qVoted[14:12] == 3'b001 && mem_rdata_qVoted[31:25] == 7'b0000000;
			instr_srli  <= is_alu_reg_immVoted && mem_rdata_qVoted[14:12] == 3'b101 && mem_rdata_qVoted[31:25] == 7'b0000000;
			instr_srai  <= is_alu_reg_immVoted && mem_rdata_qVoted[14:12] == 3'b101 && mem_rdata_qVoted[31:25] == 7'b0100000;

			instr_add   <= is_alu_reg_regVoted && mem_rdata_qVoted[14:12] == 3'b000 && mem_rdata_qVoted[31:25] == 7'b0000000;
			instr_sub   <= is_alu_reg_regVoted && mem_rdata_qVoted[14:12] == 3'b000 && mem_rdata_qVoted[31:25] == 7'b0100000;
			instr_sll   <= is_alu_reg_regVoted && mem_rdata_qVoted[14:12] == 3'b001 && mem_rdata_qVoted[31:25] == 7'b0000000;
			instr_slt   <= is_alu_reg_regVoted && mem_rdata_qVoted[14:12] == 3'b010 && mem_rdata_qVoted[31:25] == 7'b0000000;
			instr_sltu  <= is_alu_reg_regVoted && mem_rdata_qVoted[14:12] == 3'b011 && mem_rdata_qVoted[31:25] == 7'b0000000;
			instr_xor   <= is_alu_reg_regVoted && mem_rdata_qVoted[14:12] == 3'b100 && mem_rdata_qVoted[31:25] == 7'b0000000;
			instr_srl   <= is_alu_reg_regVoted && mem_rdata_qVoted[14:12] == 3'b101 && mem_rdata_qVoted[31:25] == 7'b0000000;
			instr_sra   <= is_alu_reg_regVoted && mem_rdata_qVoted[14:12] == 3'b101 && mem_rdata_qVoted[31:25] == 7'b0100000;
			instr_or    <= is_alu_reg_regVoted && mem_rdata_qVoted[14:12] == 3'b110 && mem_rdata_qVoted[31:25] == 7'b0000000;
			instr_and   <= is_alu_reg_regVoted && mem_rdata_qVoted[14:12] == 3'b111 && mem_rdata_qVoted[31:25] == 7'b0000000;

			instr_rdcycle  <= ((mem_rdata_qVoted[6:0] == 7'b1110011 && mem_rdata_qVoted[31:12] == 'b11000000000000000010) ||
			                   (mem_rdata_qVoted[6:0] == 7'b1110011 && mem_rdata_qVoted[31:12] == 'b11000000000100000010)) && ENABLE_COUNTERS;
			instr_rdcycleh <= ((mem_rdata_qVoted[6:0] == 7'b1110011 && mem_rdata_qVoted[31:12] == 'b11001000000000000010) ||
			                   (mem_rdata_qVoted[6:0] == 7'b1110011 && mem_rdata_qVoted[31:12] == 'b11001000000100000010)) && ENABLE_COUNTERS && ENABLE_COUNTERS64;
			instr_rdinstr  <=  (mem_rdata_qVoted[6:0] == 7'b1110011 && mem_rdata_qVoted[31:12] == 'b11000000001000000010) && ENABLE_COUNTERS;
			instr_rdinstrh <=  (mem_rdata_qVoted[6:0] == 7'b1110011 && mem_rdata_qVoted[31:12] == 'b11001000001000000010) && ENABLE_COUNTERS && ENABLE_COUNTERS64;

			instr_ecall_ebreak <= ((mem_rdata_qVoted[6:0] == 7'b1110011 && (!mem_rdata_qVoted[31:21]) && (!mem_rdata_qVoted[19:7])) ||
					(COMPRESSED_ISA && mem_rdata_qVoted[15:0] == 16'h9002));

			instr_getq    <= mem_rdata_qVoted[6:0] == 7'b0001011 && mem_rdata_qVoted[31:25] == 7'b0000000 && ENABLE_IRQ && ENABLE_IRQ_QREGS;
			instr_setq    <= mem_rdata_qVoted[6:0] == 7'b0001011 && mem_rdata_qVoted[31:25] == 7'b0000001 && ENABLE_IRQ && ENABLE_IRQ_QREGS;
			instr_maskirq <= mem_rdata_qVoted[6:0] == 7'b0001011 && mem_rdata_qVoted[31:25] == 7'b0000011 && ENABLE_IRQ;
			instr_timer   <= mem_rdata_qVoted[6:0] == 7'b0001011 && mem_rdata_qVoted[31:25] == 7'b0000101 && ENABLE_IRQ && ENABLE_IRQ_TIMER;

			is_slli_srli_srai <= is_alu_reg_immVoted && (|{
				mem_rdata_qVoted[14:12] == 3'b001 && mem_rdata_qVoted[31:25] == 7'b0000000,
				mem_rdata_qVoted[14:12] == 3'b101 && mem_rdata_qVoted[31:25] == 7'b0000000,
				mem_rdata_qVoted[14:12] == 3'b101 && mem_rdata_qVoted[31:25] == 7'b0100000
			});

			is_jalr_addi_slti_sltiu_xori_ori_andi <= instr_jalrVoted || is_alu_reg_immVoted && (|{
				mem_rdata_qVoted[14:12] == 3'b000,
				mem_rdata_qVoted[14:12] == 3'b010,
				mem_rdata_qVoted[14:12] == 3'b011,
				mem_rdata_qVoted[14:12] == 3'b100,
				mem_rdata_qVoted[14:12] == 3'b110,
				mem_rdata_qVoted[14:12] == 3'b111
			});

			is_sll_srl_sra <= is_alu_reg_regVoted && (|{
				mem_rdata_qVoted[14:12] == 3'b001 && mem_rdata_qVoted[31:25] == 7'b0000000,
				mem_rdata_qVoted[14:12] == 3'b101 && mem_rdata_qVoted[31:25] == 7'b0000000,
				mem_rdata_qVoted[14:12] == 3'b101 && mem_rdata_qVoted[31:25] == 7'b0100000
			});

			is_lui_auipc_jal_jalr_addi_add_sub <= 0;
			is_compare <= 0;

			(* parallel_case *)
			case (1'b1)
				instr_jalVoted:
					decoded_imm <= decoded_imm_jVoted;
				|{instr_luiVoted, instr_auipcVoted}:
					decoded_imm <= mem_rdata_qVoted[31:12] << 12;
				|{instr_jalrVoted, is_lb_lh_lw_lbu_lhuVoted, is_alu_reg_immVoted}:
					decoded_imm <= $signed(mem_rdata_qVoted[31:20]);
				is_beq_bne_blt_bge_bltu_bgeuVoted:
					decoded_imm <= $signed({mem_rdata_qVoted[31], mem_rdata_qVoted[7], mem_rdata_qVoted[30:25], mem_rdata_qVoted[11:8], 1'b0});
				is_sb_sh_swVoted:
					decoded_imm <= $signed({mem_rdata_qVoted[31:25], mem_rdata_qVoted[11:7]});
				default:
					decoded_imm <= 1'bx;
			endcase
		end

		if (!rstn) begin
			is_beq_bne_blt_bge_bltu_bgeu <= 0;
			is_compare <= 0;

			instr_beq   <= 0;
			instr_bne   <= 0;
			instr_blt   <= 0;
			instr_bge   <= 0;
			instr_bltu  <= 0;
			instr_bgeu  <= 0;

			instr_addi  <= 0;
			instr_slti  <= 0;
			instr_sltiu <= 0;
			instr_xori  <= 0;
			instr_ori   <= 0;
			instr_andi  <= 0;

			instr_add   <= 0;
			instr_sub   <= 0;
			instr_sll   <= 0;
			instr_slt   <= 0;
			instr_sltu  <= 0;
			instr_xor   <= 0;
			instr_srl   <= 0;
			instr_sra   <= 0;
			instr_or    <= 0;
			instr_and   <= 0;
		end
	end


	// Main State Machine

	localparam cpu_state_trap   = 8'b10000000;
	localparam cpu_state_fetch  = 8'b01000000;
	localparam cpu_state_ld_rs1 = 8'b00100000;
	localparam cpu_state_ld_rs2 = 8'b00010000;
	localparam cpu_state_exec   = 8'b00001000;
	localparam cpu_state_shift  = 8'b00000100;
	localparam cpu_state_stmem  = 8'b00000010;
	localparam cpu_state_ldmem  = 8'b00000001;

	reg [7:0] cpu_state;
	wire [7:0] cpu_stateVoted = cpu_state;
	reg [1:0] irq_state;
	wire [1:0] irq_stateVoted = irq_state;

	/*`FORMAL_KEEP*/ reg [127:0] dbg_ascii_state;

	always @* begin
		dbg_ascii_state = "";
		if (cpu_stateVoted == cpu_state_trap)   dbg_ascii_state = "trap";
		if (cpu_stateVoted == cpu_state_fetch)  dbg_ascii_state = "fetch";
		if (cpu_stateVoted == cpu_state_ld_rs1) dbg_ascii_state = "ld_rs1";
		if (cpu_stateVoted == cpu_state_ld_rs2) dbg_ascii_state = "ld_rs2";
		if (cpu_stateVoted == cpu_state_exec)   dbg_ascii_state = "exec";
		if (cpu_stateVoted == cpu_state_shift)  dbg_ascii_state = "shift";
		if (cpu_stateVoted == cpu_state_stmem)  dbg_ascii_state = "stmem";
		if (cpu_stateVoted == cpu_state_ldmem)  dbg_ascii_state = "ldmem";
	end

	reg set_mem_do_rinst;
	reg set_mem_do_rdata;
	reg set_mem_do_wdata;

	reg latched_store;
	wire latched_storeVoted = latched_store;
	reg latched_stalu;
	wire latched_staluVoted = latched_stalu;
	reg latched_branch;
	wire latched_branchVoted = latched_branch;
	reg latched_compr;
	wire latched_comprVoted = latched_compr;
	reg latched_trace;
	wire latched_traceVoted = latched_trace;
	reg latched_is_lu;
	wire latched_is_luVoted = latched_is_lu;
	reg latched_is_lh;
	wire latched_is_lhVoted = latched_is_lh;
	reg latched_is_lb;
	wire latched_is_lbVoted = latched_is_lb;
	reg [cpuregindex_bits-1:0] latched_rd;
	wire [cpuregindex_bits-1:0] latched_rdVoted = latched_rd;

	reg [31:0] current_pc;
	assign next_pc = latched_storeVoted && latched_branchVoted ? reg_outVoted & ~1 : reg_next_pcVoted;

	reg [3:0] pcpi_timeout_counter;
	reg pcpi_timeout;

	reg [31:0] next_irq_pending;
	reg do_waitirq;
	wire do_waitirqVoted = do_waitirq;


	// -----------------------------------
	// <ALU
	reg [31:0] alu_out, alu_out_q;
	wire [31:0] alu_out_qVoted = alu_out_q;
	reg alu_out_0, alu_out_0_q;
	reg alu_wait, alu_wait_2;
	wire alu_waitVoted = alu_wait;
	wire alu_wait_2Voted = alu_wait_2;

	reg [31:0] alu_add_sub;
	reg [31:0] alu_shl, alu_shr;
	reg alu_eq, alu_ltu, alu_lts;

	// generate if (TWO_CYCLE_ALU) begin
	// 	always @(posedge clk) begin
	// 		alu_add_sub <= instr_subVoted ? reg_op1Voted - reg_op2Voted : reg_op1Voted + reg_op2Voted;
	// 		alu_eq <= reg_op1Voted == reg_op2Voted;
	// 		alu_lts <= $signed(reg_op1Voted) < $signed(reg_op2Voted);
	// 		alu_ltu <= reg_op1Voted < reg_op2Voted;
	// 		alu_shl <= reg_op1Voted << reg_op2Voted[4:0];
	// 		alu_shr <= $signed({instr_sraVoted || instr_sraiVoted ? reg_op1Voted[31] : 1'b0, reg_op1Voted}) >>> reg_op2Voted[4:0];
	// 	end
	// end else begin
		always @* begin
			alu_add_sub = instr_subVoted ? reg_op1Voted - reg_op2Voted : reg_op1Voted + reg_op2Voted;
			alu_eq = reg_op1Voted == reg_op2Voted;
			alu_lts = $signed(reg_op1Voted) < $signed(reg_op2Voted);
			alu_ltu = reg_op1Voted < reg_op2Voted;
			alu_shl = reg_op1Voted << reg_op2Voted[4:0];
			alu_shr = $signed({instr_sraVoted || instr_sraiVoted ? reg_op1Voted[31] : 1'b0, reg_op1Voted}) >>> reg_op2Voted[4:0];
		end
	// end endgenerate

	always @* begin
		alu_out_0 = 'bx;
		(* parallel_case, full_case *)
		case (1'b1)
			instr_beqVoted:
				alu_out_0 = alu_eq;
			instr_bneVoted:
				alu_out_0 = !alu_eq;
			instr_bgeVoted:
				alu_out_0 = !alu_lts;
			instr_bgeuVoted:
				alu_out_0 = !alu_ltu;
			is_slti_blt_sltVoted && (!TWO_CYCLE_COMPARE || !{instr_beqVoted,instr_bneVoted,instr_bgeVoted,instr_bgeuVoted}):
				alu_out_0 = alu_lts;
			is_sltiu_bltu_sltuVoted && (!TWO_CYCLE_COMPARE || !{instr_beqVoted,instr_bneVoted,instr_bgeVoted,instr_bgeuVoted}):
				alu_out_0 = alu_ltu;
		endcase

		alu_out = 'bx;
		(* parallel_case, full_case *)
		case (1'b1)
			is_lui_auipc_jal_jalr_addi_add_subVoted:
				alu_out = alu_add_sub;
			is_compareVoted:
				alu_out = alu_out_0;
			instr_xoriVoted || instr_xorVoted:
				alu_out = reg_op1Voted ^ reg_op2Voted;
			instr_oriVoted || instr_orVoted:
				alu_out = reg_op1Voted | reg_op2Voted;
			instr_andiVoted || instr_andVoted:
				alu_out = reg_op1Voted & reg_op2Voted;
			BARREL_SHIFTER && (instr_sllVoted || instr_slliVoted):
				alu_out = alu_shl;
			BARREL_SHIFTER && (instr_srlVoted || instr_srliVoted || instr_sraVoted || instr_sraiVoted):
				alu_out = alu_shr;
		endcase

// `ifdef RISCV_FORMAL_BLACKBOX_ALU
// 		alu_out_0 = $anyseq;
// 		alu_out = $anyseq;
// `endif
	end

	// ALU>
	// -----------------------------------

	reg clear_prefetched_high_word_q;
	wire clear_prefetched_high_word_qVoted = clear_prefetched_high_word_q;
	always @(posedge clk) clear_prefetched_high_word_q <= clear_prefetched_high_word;

	always @* begin
		clear_prefetched_high_word = clear_prefetched_high_word_qVoted;
		if (!prefetched_high_wordVoted)
			clear_prefetched_high_word = 0;
		if (latched_branchVoted || irq_stateVoted || !rstn)
			clear_prefetched_high_word = COMPRESSED_ISA;
	end

	reg cpuregs_write;
	reg [31:0] cpuregs_wrdata;
	reg [31:0] cpuregs_rs1;
	reg [31:0] cpuregs_rs2;
	reg [cpuregindex_bits-1:0] decoded_rs;

	always @* begin
		cpuregs_write = 0;
		cpuregs_wrdata = 'bx;

		if (cpu_stateVoted == cpu_state_fetch) begin
			(* parallel_case *)
			case (1'b1)
				latched_branchVoted: begin
					cpuregs_wrdata = reg_pcVoted + (latched_comprVoted ? 2 : 4);
					cpuregs_write = 1;
				end
				latched_storeVoted && (!latched_branchVoted): begin
					cpuregs_wrdata = latched_staluVoted ? alu_out_qVoted : reg_outVoted;
					cpuregs_write = 1;
				end
				ENABLE_IRQ && irq_stateVoted[0]: begin
					cpuregs_wrdata = reg_next_pcVoted | latched_comprVoted;
					cpuregs_write = 1;
				end
				ENABLE_IRQ && irq_stateVoted[1]: begin
					cpuregs_wrdata = irq_pendingVoted & ~irq_maskVoted;
					cpuregs_write = 1;
				end
			endcase
		end
	end

	// -----------------------------------
	// <REGISTER FILE
// `ifndef PICORV32_REGS
	integer k;
	always @(posedge clk) begin
		for (k = 0; k < cpuregfile_size; k = k+1)
			cpuregs[k] <= cpuregsVoted[k];

		if (rstn && cpuregs_write && latched_rdVoted)
// `ifdef PICORV32_TESTBUG_001
// 			cpuregs[latched_rdVoted ^ 1] <= cpuregs_wrdata;
// `elsif PICORV32_TESTBUG_002
// 			cpuregs[latched_rdVoted] <= cpuregs_wrdata ^ 1;
// `else
			cpuregs[latched_rdVoted] <= cpuregs_wrdata;
// `endif
	end

	always @* begin
		decoded_rs = 'bx;
		if (ENABLE_REGS_DUALPORT) begin
// `ifndef RISCV_FORMAL_BLACKBOX_REGS
			cpuregs_rs1 = decoded_rs1Voted ? cpuregsVoted[decoded_rs1Voted] : 0;
			cpuregs_rs2 = decoded_rs2Voted ? cpuregsVoted[decoded_rs2Voted] : 0;
// `else
// 			cpuregs_rs1 = decoded_rs1Voted ? $anyseq : 0;
// 			cpuregs_rs2 = decoded_rs2Voted ? $anyseq : 0;
// `endif
		end else begin
			decoded_rs = (cpu_stateVoted == cpu_state_ld_rs2) ? decoded_rs2Voted : decoded_rs1Voted;
// `ifndef RISCV_FORMAL_BLACKBOX_REGS
			cpuregs_rs1 = decoded_rs ? cpuregsVoted[decoded_rs] : 0;
// `else
// 			cpuregs_rs1 = decoded_rs ? $anyseq : 0;
// `endif
			cpuregs_rs2 = cpuregs_rs1;
		end
	end
// `else
// 	wire[31:0] cpuregs_rdata1;
// 	wire[31:0] cpuregs_rdata2;

// 	wire [5:0] cpuregs_waddr = latched_rdVoted;
// 	wire [5:0] cpuregs_raddr1 = ENABLE_REGS_DUALPORT ? decoded_rs1Voted : decoded_rs;
// 	wire [5:0] cpuregs_raddr2 = ENABLE_REGS_DUALPORT ? decoded_rs2Voted : 0;

// 	`PICORV32_REGS cpuregs (
// 		.clk(clk),
// 		.wen(rstn && cpuregs_write && latched_rdVoted),
// 		.waddr(cpuregs_waddr),
// 		.raddr1(cpuregs_raddr1),
// 		.raddr2(cpuregs_raddr2),
// 		.wdata(cpuregs_wrdata),
// 		.rdata1(cpuregs_rdata1),
// 		.rdata2(cpuregs_rdata2)
// 	);

// 	always @* begin
// 		decoded_rs = 'bx;
// 		if (ENABLE_REGS_DUALPORT) begin
// 			cpuregs_rs1 = decoded_rs1Voted ? cpuregs_rdata1 : 0;
// 			cpuregs_rs2 = decoded_rs2Voted ? cpuregs_rdata2 : 0;
// 		end else begin
// 			decoded_rs = (cpu_stateVoted == cpu_state_ld_rs2) ? decoded_rs2Voted : decoded_rs1Voted;
// 			cpuregs_rs1 = decoded_rs ? cpuregs_rdata1 : 0;
// 			cpuregs_rs2 = cpuregs_rs1;
// 		end
// 	end
// `endif
	// REGISTER FILE>
	// -----------------------------------

	// -----------------------------------
	// <CPU STATE MACHINE
	assign launch_next_insn = cpu_stateVoted == cpu_state_fetch && decoder_triggerVoted && (!ENABLE_IRQ || irq_delayVoted || irq_activeVoted || !(irq_pendingVoted & ~irq_maskVoted));

	always @(posedge clk) begin
		count_cycle					<= count_cycleVoted;
		count_instr					<= count_instrVoted;
		timer						<= timerVoted;
		decoder_trigger				<= decoder_triggerVoted;
		decoder_pseudo_trigger		<= decoder_pseudo_triggerVoted;
		do_waitirq					<= do_waitirqVoted;
		trace_valid_int				<= trace_valid_intVoted;
		trace_data_int				<= trace_data_intVoted;
		reg_pc						<= reg_pcVoted;
		reg_next_pc					<= reg_next_pcVoted;
		latched_store				<= latched_storeVoted;
		latched_stalu				<= latched_staluVoted;
		latched_branch				<= latched_branchVoted;
		latched_trace				<= latched_traceVoted;
		latched_is_lu				<= latched_is_luVoted;
		latched_is_lh				<= latched_is_lhVoted;
		latched_is_lb				<= latched_is_lbVoted;
		irq_active					<= irq_activeVoted;
		irq_delay					<= irq_delayVoted;
		irq_mask					<= irq_maskVoted;
		irq_state					<= irq_stateVoted;
		eoi_int						<= eoi_intVoted;
		latched_rd					<= latched_rdVoted;
		cpu_state					<= cpu_stateVoted;
		mem_do_rinst				<= mem_do_rinstVoted;
		mem_wordsize				<= mem_wordsizeVoted;
		latched_compr				<= latched_comprVoted;
		mem_do_prefetch				<= mem_do_prefetchVoted;
		reg_op1						<= reg_op1Voted;
		reg_op2						<= reg_op2Voted;
		mem_do_rdata				<= mem_do_rdataVoted;
		mem_do_wdata				<= mem_do_wdataVoted;
		irq_pending					<= irq_pendingVoted;

		trap_int <= 0;
		reg_sh <= 'bx;
		reg_out <= 'bx;
		set_mem_do_rinst = 0;
		set_mem_do_rdata = 0;
		set_mem_do_wdata = 0;

		alu_out_0_q <= alu_out_0;
		alu_out_q <= alu_out;

		alu_wait <= 0;
		alu_wait_2 <= 0;

		if (launch_next_insn) begin
			dbg_rs1val <= 'bx;
			dbg_rs2val <= 'bx;
			dbg_rs1val_valid <= 0;
			dbg_rs2val_valid <= 0;
		end

		if (WITH_PCPI && CATCH_ILLINSN) begin
			if (rstn && pcpi_valid && (!pcpi_int_wait)) begin
				if (pcpi_timeout_counter) begin
					pcpi_timeout_counter <= pcpi_timeout_counter - 1;
				end
			end else begin
				pcpi_timeout_counter <= ~0;
			end
			pcpi_timeout <= !pcpi_timeout_counter;
		end

		if (ENABLE_COUNTERS) begin
			count_cycle <= rstn ? count_cycleVoted + 1 : 0;
			if (!ENABLE_COUNTERS64) begin
				count_cycle[63:32] <= 0;
			end
		end else begin
			count_cycle <= 'bx;
			count_instr <= 'bx;
		end

		next_irq_pending = ENABLE_IRQ ? irq_pendingVoted & LATCHED_IRQ : 'bx;

		if (ENABLE_IRQ && ENABLE_IRQ_TIMER && timerVoted) begin
			timer <= timerVoted - 1;
		end

		decoder_trigger <= mem_do_rinstVoted && mem_done;
		decoder_trigger_q <= decoder_triggerVoted;
		decoder_pseudo_trigger <= 0;
		decoder_pseudo_trigger_q <= decoder_pseudo_triggerVoted;
		do_waitirq <= 0;

		trace_valid_int <= 0;

		if (!ENABLE_TRACE) begin
			trace_data_int <= 'bx;
		end

		if (!rstn) begin
			reg_pc <= PROGADDR_RESET;
			reg_next_pc <= PROGADDR_RESET;
			if (ENABLE_COUNTERS) begin
				count_instr <= 0;
			end
			latched_store <= 0;
			latched_stalu <= 0;
			latched_branch <= 0;
			latched_trace <= 0;
			latched_is_lu <= 0;
			latched_is_lh <= 0;
			latched_is_lb <= 0;
			pcpi_valid <= 0;
			pcpi_timeout <= 0;
			irq_active <= 0;
			irq_delay <= 0;
			irq_mask <= ~0;
			next_irq_pending = 0;
			irq_state <= 0;
			eoi_int <= 0;
			timer <= 0;
			if (~STACKADDR) begin
				latched_store <= 1;
				latched_rd <= 2;
				reg_out <= STACKADDR;
			end
			cpu_state <= cpu_state_fetch;
		end else begin
			(* parallel_case, full_case *)
			case (cpu_stateVoted)
				cpu_state_trap: begin
					trap_int <= 1;
				end

				cpu_state_fetch: begin
					mem_do_rinst <= !decoder_triggerVoted && (!do_waitirqVoted);
					mem_wordsize <= 0;

					current_pc = reg_next_pcVoted;

					(* parallel_case *)
					case (1'b1)
						latched_branchVoted: begin
							current_pc = latched_storeVoted ? (latched_staluVoted ? alu_out_qVoted : reg_outVoted) & ~1 : reg_next_pcVoted;
							// `debug($display("ST_RD:  %2d 0x%08x, BRANCH 0x%08x", latched_rdVoted, reg_pcVoted + (latched_comprVoted ? 2 : 4), current_pc);)
						end
						latched_storeVoted && (!latched_branchVoted): begin
							// `debug($display("ST_RD:  %2d 0x%08x", latched_rdVoted, latched_staluVoted ? alu_out_qVoted : reg_outVoted);)
						end
						ENABLE_IRQ && irq_stateVoted[0]: begin
							current_pc = PROGADDR_IRQ;
							irq_active <= 1;
							mem_do_rinst <= 1;
						end
						ENABLE_IRQ && irq_stateVoted[1]: begin
							eoi_int <= irq_pendingVoted & ~irq_maskVoted;
							next_irq_pending = next_irq_pending & irq_maskVoted;
						end
					endcase

					if (ENABLE_TRACE && latched_traceVoted) begin
						latched_trace <= 0;
						trace_valid_int <= 1;
						if (latched_branchVoted) begin
							trace_data_int <= (irq_activeVoted ? TRACE_IRQ : 0) | TRACE_BRANCH | (current_pc & 32'hfffffffe);
						end else begin
							trace_data_int <= (irq_activeVoted ? TRACE_IRQ : 0) | (latched_staluVoted ? alu_out_qVoted : reg_outVoted);
						end
					end

					reg_pc <= current_pc;
					reg_next_pc <= current_pc;

					latched_store <= 0;
					latched_stalu <= 0;
					latched_branch <= 0;
					latched_is_lu <= 0;
					latched_is_lh <= 0;
					latched_is_lb <= 0;
					latched_rd <= decoded_rdVoted;
					latched_compr <= compressed_instrVoted;

					if (ENABLE_IRQ && ((decoder_triggerVoted && (!irq_activeVoted) && (!irq_delayVoted) && (|(irq_pendingVoted & ~irq_maskVoted))) || irq_stateVoted)) begin
						irq_state <=
							irq_stateVoted == 2'b00 ? 2'b01 :
							irq_stateVoted == 2'b01 ? 2'b10 : 2'b00;
						latched_compr <= latched_comprVoted;
						if (ENABLE_IRQ_QREGS) begin
							latched_rd <= irqregs_offset | irq_stateVoted[0];
						end else begin
							latched_rd <= irq_stateVoted[0] ? 4 : 3;
						end
					end else begin
						if (ENABLE_IRQ && (decoder_triggerVoted || do_waitirqVoted) && instr_waitirqVoted) begin
							if (irq_pendingVoted) begin
								latched_store <= 1;
								reg_out <= irq_pendingVoted;
								reg_next_pc <= current_pc + (compressed_instrVoted ? 2 : 4);
								mem_do_rinst <= 1;
							end else begin
								do_waitirq <= 1;
							end
						end else begin
							if (decoder_triggerVoted) begin
								// `debug($display("-- %-0t", $time);)
								irq_delay <= irq_activeVoted;
								reg_next_pc <= current_pc + (compressed_instrVoted ? 2 : 4);
								if (ENABLE_TRACE) begin
									latched_trace <= 1;
								end
								if (ENABLE_COUNTERS) begin
									count_instr <= count_instrVoted + 1;
									if (!ENABLE_COUNTERS64) begin
										count_instr[63:32] <= 0;
									end
								end
								if (instr_jalVoted) begin
									mem_do_rinst <= 1;
									reg_next_pc <= current_pc + decoded_imm_jVoted;
									latched_branch <= 1;
								end else begin
									mem_do_rinst <= 0;
									mem_do_prefetch <= !instr_jalrVoted && (!instr_retirqVoted);
									cpu_state <= cpu_state_ld_rs1;
								end
							end
						end
					end
				end

				cpu_state_ld_rs1: begin
					reg_op1 <= 'bx;
					reg_op2 <= 'bx;

					(* parallel_case *)
					case (1'b1)
						(CATCH_ILLINSN || WITH_PCPI) && instr_trap: begin
							if (WITH_PCPI) begin
								// `debug($display("LD_RS1: %2d 0x%08x", decoded_rs1Voted, cpuregs_rs1);)
								reg_op1 <= cpuregs_rs1;
								dbg_rs1val <= cpuregs_rs1;
								dbg_rs1val_valid <= 1;
								if (ENABLE_REGS_DUALPORT) begin
									pcpi_valid <= 1;
									// `debug($display("LD_RS2: %2d 0x%08x", decoded_rs2Voted, cpuregs_rs2);)
									reg_sh <= cpuregs_rs2;
									reg_op2 <= cpuregs_rs2;
									dbg_rs2val <= cpuregs_rs2;
									dbg_rs2val_valid <= 1;
									if (pcpi_int_ready) begin
										mem_do_rinst <= 1;
										pcpi_valid <= 0;
										reg_out <= pcpi_int_rd;
										latched_store <= pcpi_int_wr;
										cpu_state <= cpu_state_fetch;
									end else begin
										if (CATCH_ILLINSN && (pcpi_timeout || instr_ecall_ebreak)) begin
											pcpi_valid <= 0;
											// `debug($display("EBREAK OR UNSUPPORTED INSN AT 0x%08x", reg_pcVoted);)
											if (ENABLE_IRQ && (!irq_maskVoted[irq_ebreak]) && (!irq_activeVoted)) begin
												next_irq_pending[irq_ebreak] = 1;
												cpu_state <= cpu_state_fetch;
											end else begin
												cpu_state <= cpu_state_trap;
											end
										end
									end
								end else begin
									cpu_state <= cpu_state_ld_rs2;
								end
							end else begin
								// `debug($display("EBREAK OR UNSUPPORTED INSN AT 0x%08x", reg_pcVoted);)
								if (ENABLE_IRQ && (!irq_maskVoted[irq_ebreak]) && (!irq_activeVoted)) begin
									next_irq_pending[irq_ebreak] = 1;
									cpu_state <= cpu_state_fetch;
								end else begin
									cpu_state <= cpu_state_trap;
								end
							end
						end
						ENABLE_COUNTERS && is_rdcycle_rdcycleh_rdinstr_rdinstrh: begin
							(* parallel_case, full_case *)
							case (1'b1)
								instr_rdcycleVoted:
									reg_out <= count_cycleVoted[31:0];
								instr_rdcyclehVoted && ENABLE_COUNTERS64:
									reg_out <= count_cycleVoted[63:32];
								instr_rdinstrVoted:
									reg_out <= count_instrVoted[31:0];
								instr_rdinstrhVoted && ENABLE_COUNTERS64:
									reg_out <= count_instrVoted[63:32];
							endcase
							latched_store <= 1;
							cpu_state <= cpu_state_fetch;
						end
						is_lui_auipc_jalVoted: begin
							reg_op1 <= instr_luiVoted ? 0 : reg_pcVoted;
							reg_op2 <= decoded_immVoted;
							if (TWO_CYCLE_ALU) begin
								alu_wait <= 1;
							end else begin
								mem_do_rinst <= mem_do_prefetchVoted;
							end
							cpu_state <= cpu_state_exec;
						end
						ENABLE_IRQ && ENABLE_IRQ_QREGS && instr_getqVoted: begin
							// `debug($display("LD_RS1: %2d 0x%08x", decoded_rs1, cpuregs_rs1);)
							reg_out <= cpuregs_rs1;
							dbg_rs1val <= cpuregs_rs1;
							dbg_rs1val_valid <= 1;
							latched_store <= 1;
							cpu_state <= cpu_state_fetch;
						end
						ENABLE_IRQ && ENABLE_IRQ_QREGS && instr_setqVoted: begin
							// `debug($display("LD_RS1: %2d 0x%08x", decoded_rs1, cpuregs_rs1);)
							reg_out <= cpuregs_rs1;
							dbg_rs1val <= cpuregs_rs1;
							dbg_rs1val_valid <= 1;
							latched_rd <= latched_rdVoted | irqregs_offset;
							latched_store <= 1;
							cpu_state <= cpu_state_fetch;
						end
						ENABLE_IRQ && instr_retirqVoted: begin
							eoi_int <= 0;
							irq_active <= 0;
							latched_branch <= 1;
							latched_store <= 1;
							// `debug($display("LD_RS1: %2d 0x%08x", decoded_rs1Voted, cpuregs_rs1);)
							reg_out <= CATCH_MISALIGN ? (cpuregs_rs1 & 32'h fffffffe) : cpuregs_rs1;
							dbg_rs1val <= cpuregs_rs1;
							dbg_rs1val_valid <= 1;
							cpu_state <= cpu_state_fetch;
						end
						ENABLE_IRQ && instr_maskirqVoted: begin
							latched_store <= 1;
							reg_out <= irq_maskVoted;
							// `debug($display("LD_RS1: %2d 0x%08x", decoded_rs1Voted, cpuregs_rs1);)
							irq_mask <= cpuregs_rs1 | MASKED_IRQ;
							dbg_rs1val <= cpuregs_rs1;
							dbg_rs1val_valid <= 1;
							cpu_state <= cpu_state_fetch;
						end
						ENABLE_IRQ && ENABLE_IRQ_TIMER && instr_timerVoted: begin
							latched_store <= 1;
							reg_out <= timerVoted;
							// `debug($display("LD_RS1: %2d 0x%08x", decoded_rs1Voted, cpuregs_rs1);)
							timer <= cpuregs_rs1;
							dbg_rs1val <= cpuregs_rs1;
							dbg_rs1val_valid <= 1;
							cpu_state <= cpu_state_fetch;
						end
						is_lb_lh_lw_lbu_lhuVoted && (!instr_trap): begin
							// `debug($display("LD_RS1: %2d 0x%08x", decoded_rs1, cpuregs_rs1);)
							reg_op1 <= cpuregs_rs1;
							dbg_rs1val <= cpuregs_rs1;
							dbg_rs1val_valid <= 1;
							cpu_state <= cpu_state_ldmem;
							mem_do_rinst <= 1;
						end
						is_slli_srli_sraiVoted && (!BARREL_SHIFTER): begin
							// `debug($display("LD_RS1: %2d 0x%08x", decoded_rs1, cpuregs_rs1);)
							reg_op1 <= cpuregs_rs1;
							dbg_rs1val <= cpuregs_rs1;
							dbg_rs1val_valid <= 1;
							reg_sh <= decoded_rs2Voted;
							cpu_state <= cpu_state_shift;
						end
						is_jalr_addi_slti_sltiu_xori_ori_andiVoted, is_slli_srli_sraiVoted && BARREL_SHIFTER: begin
							// `debug($display("LD_RS1: %2d 0x%08x", decoded_rs1, cpuregs_rs1);)
							reg_op1 <= cpuregs_rs1;
							dbg_rs1val <= cpuregs_rs1;
							dbg_rs1val_valid <= 1;
							reg_op2 <= is_slli_srli_sraiVoted && BARREL_SHIFTER ? decoded_rs2Voted : decoded_immVoted;
							if (TWO_CYCLE_ALU) begin
								alu_wait <= 1;
							end else begin
								mem_do_rinst <= mem_do_prefetchVoted;
							end
							cpu_state <= cpu_state_exec;
						end
						default: begin
							// `debug($display("LD_RS1: %2d 0x%08x", decoded_rs1Voted, cpuregs_rs1);)
							reg_op1 <= cpuregs_rs1;
							dbg_rs1val <= cpuregs_rs1;
							dbg_rs1val_valid <= 1;
							if (ENABLE_REGS_DUALPORT) begin
								// `debug($display("LD_RS2: %2d 0x%08x", decoded_rs2Voted, cpuregs_rs2);)
								reg_sh <= cpuregs_rs2;
								reg_op2 <= cpuregs_rs2;
								dbg_rs2val <= cpuregs_rs2;
								dbg_rs2val_valid <= 1;
								(* parallel_case *)
								case (1'b1)
									is_sb_sh_swVoted: begin
										cpu_state <= cpu_state_stmem;
										mem_do_rinst <= 1;
									end
									is_sll_srl_sraVoted && (!BARREL_SHIFTER): begin
										cpu_state <= cpu_state_shift;
									end
									default: begin
										if (TWO_CYCLE_ALU || (TWO_CYCLE_COMPARE && is_beq_bne_blt_bge_bltu_bgeuVoted)) begin
											alu_wait_2 <= TWO_CYCLE_ALU && (TWO_CYCLE_COMPARE && is_beq_bne_blt_bge_bltu_bgeuVoted);
											alu_wait <= 1;
										end else begin
											mem_do_rinst <= mem_do_prefetchVoted;
										end
										cpu_state <= cpu_state_exec;
									end
								endcase
							end else begin
								cpu_state <= cpu_state_ld_rs2;
							end
						end
					endcase
				end

				cpu_state_ld_rs2: begin
					// `debug($display("LD_RS2: %2d 0x%08x", decoded_rs2Voted, cpuregs_rs2);)
					reg_sh <= cpuregs_rs2;
					reg_op2 <= cpuregs_rs2;
					dbg_rs2val <= cpuregs_rs2;
					dbg_rs2val_valid <= 1;

					(* parallel_case *)
					case (1'b1)
						WITH_PCPI && instr_trap: begin
							pcpi_valid <= 1;
							if (pcpi_int_ready) begin
								mem_do_rinst <= 1;
								pcpi_valid <= 0;
								reg_out <= pcpi_int_rd;
								latched_store <= pcpi_int_wr;
								cpu_state <= cpu_state_fetch;
							end else begin
								if (CATCH_ILLINSN && (pcpi_timeout || instr_ecall_ebreak)) begin
									pcpi_valid <= 0;
									// `debug($display("EBREAK OR UNSUPPORTED INSN AT 0x%08x", reg_pcVoted);)
									if (ENABLE_IRQ && (!irq_maskVoted[irq_ebreak]) && (!irq_activeVoted)) begin
										next_irq_pending[irq_ebreak] = 1;
										cpu_state <= cpu_state_fetch;
									end else begin
										cpu_state <= cpu_state_trap;
									end
								end
							end
						end
						is_sb_sh_swVoted: begin
							cpu_state <= cpu_state_stmem;
							mem_do_rinst <= 1;
						end
						is_sll_srl_sraVoted && (!BARREL_SHIFTER): begin
							cpu_state <= cpu_state_shift;
						end
						default: begin
							if (TWO_CYCLE_ALU || (TWO_CYCLE_COMPARE && is_beq_bne_blt_bge_bltu_bgeuVoted)) begin
								alu_wait_2 <= TWO_CYCLE_ALU && (TWO_CYCLE_COMPARE && is_beq_bne_blt_bge_bltu_bgeuVoted);
								alu_wait <= 1;
							end else begin
								mem_do_rinst <= mem_do_prefetchVoted;
							end
							cpu_state <= cpu_state_exec;
						end
					endcase
				end

				cpu_state_exec: begin
					reg_out <= reg_pcVoted + decoded_immVoted;
					if ((TWO_CYCLE_ALU || TWO_CYCLE_COMPARE) && (alu_waitVoted || alu_wait_2Voted)) begin
						mem_do_rinst <= mem_do_prefetchVoted && (!alu_wait_2Voted);
						alu_wait <= alu_wait_2Voted;
					end else begin
						if (is_beq_bne_blt_bge_bltu_bgeuVoted) begin
							latched_rd <= 0;
							latched_store <= TWO_CYCLE_COMPARE ? alu_out_0_q : alu_out_0;
							latched_branch <= TWO_CYCLE_COMPARE ? alu_out_0_q : alu_out_0;
							if (mem_done) begin
								cpu_state <= cpu_state_fetch;
							end
							if (TWO_CYCLE_COMPARE ? alu_out_0_q : alu_out_0) begin
								decoder_trigger <= 0;
								set_mem_do_rinst = 1;
								// mem_do_rinst <= 1;
							end
						end else begin
							latched_branch <= instr_jalrVoted;
							latched_store <= 1;
							latched_stalu <= 1;
							cpu_state <= cpu_state_fetch;
						end
					end
				end

				cpu_state_shift: begin
					latched_store <= 1;
					if (reg_shVoted == 0) begin
						reg_out <= reg_op1Voted;
						mem_do_rinst <= mem_do_prefetchVoted;
						cpu_state <= cpu_state_fetch;
					end else begin
						if (TWO_STAGE_SHIFT && reg_shVoted >= 4) begin
							(* parallel_case, full_case *)
							case (1'b1)
								instr_slliVoted || instr_sllVoted: reg_op1 <= reg_op1Voted << 4;
								instr_srliVoted || instr_srlVoted: reg_op1 <= reg_op1Voted >> 4;
								instr_sraiVoted || instr_sraVoted: reg_op1 <= $signed(reg_op1Voted) >>> 4;
							endcase
							reg_sh <= reg_shVoted - 4;
						end else begin
							(* parallel_case, full_case *)
							case (1'b1)
								instr_slliVoted || instr_sllVoted: reg_op1 <= reg_op1Voted << 1;
								instr_srliVoted || instr_srlVoted: reg_op1 <= reg_op1Voted >> 1;
								instr_sraiVoted || instr_sraVoted: reg_op1 <= $signed(reg_op1Voted) >>> 1;
							endcase
							reg_sh <= reg_shVoted - 1;
						end
					end
				end

				cpu_state_stmem: begin
					if (ENABLE_TRACE) begin
						reg_out <= reg_op2Voted;
					end
					if (!mem_do_prefetchVoted || mem_done) begin
						if (!mem_do_wdataVoted) begin
							(* parallel_case, full_case *)
							case (1'b1)
								instr_sbVoted: mem_wordsize <= 2;
								instr_shVoted: mem_wordsize <= 1;
								instr_swVoted: mem_wordsize <= 0;
							endcase
							if (ENABLE_TRACE) begin
								trace_valid_int <= 1;
								trace_data_int <= (irq_activeVoted ? TRACE_IRQ : 0) | TRACE_ADDR | ((reg_op1Voted + decoded_immVoted) & 32'hffffffff);
							end
							reg_op1 <= reg_op1Voted + decoded_immVoted;
							set_mem_do_wdata = 1;
							// mem_do_wdata <= 1;
						end
						if (!mem_do_prefetchVoted && mem_done) begin
							cpu_state <= cpu_state_fetch;
							decoder_trigger <= 1;
							decoder_pseudo_trigger <= 1;
						end
					end
				end

				cpu_state_ldmem: begin
					latched_store <= 1;
					if (!mem_do_prefetchVoted || mem_done) begin
						if (!mem_do_rdataVoted) begin
							(* parallel_case, full_case *)
							case (1'b1)
								instr_lbVoted || instr_lbuVoted: mem_wordsize <= 2;
								instr_lhVoted || instr_lhuVoted: mem_wordsize <= 1;
								instr_lwVoted: mem_wordsize <= 0;
							endcase
							latched_is_lu <= is_lbu_lhu_lwVoted;
							latched_is_lh <= instr_lhVoted;
							latched_is_lb <= instr_lbVoted;
							if (ENABLE_TRACE) begin
								trace_valid_int <= 1;
								trace_data_int <= (irq_activeVoted ? TRACE_IRQ : 0) | TRACE_ADDR | ((reg_op1Voted + decoded_immVoted) & 32'hffffffff);
							end
							reg_op1 <= reg_op1Voted + decoded_immVoted;
							set_mem_do_rdata = 1;
							// mem_do_rdata <= 1;
						end
						if (!mem_do_prefetchVoted && mem_done) begin
							(* parallel_case, full_case *)
							case (1'b1)
								latched_is_luVoted: reg_out <= mem_rdata_word;
								latched_is_lhVoted: reg_out <= $signed(mem_rdata_word[15:0]);
								latched_is_lbVoted: reg_out <= $signed(mem_rdata_word[7:0]);
							endcase
							decoder_trigger <= 1;
							decoder_pseudo_trigger <= 1;
							cpu_state <= cpu_state_fetch;
						end
					end
				end
			endcase
		end

		if (ENABLE_IRQ) begin
			next_irq_pending = next_irq_pending | irq;
			if (ENABLE_IRQ_TIMER && timerVoted) begin
				if (timerVoted - 1 == 0) begin
					next_irq_pending[irq_timer] = 1;
				end
			end
		end

		if (CATCH_MISALIGN && rstn && (mem_do_rdataVoted || mem_do_wdataVoted)) begin
			if (mem_wordsizeVoted == 0 && reg_op1Voted[1:0] != 0) begin
				// `debug($display("MISALIGNED WORD: 0x%08x", reg_op1Voted);)
				if (ENABLE_IRQ && (!irq_maskVoted[irq_buserror]) && (!irq_activeVoted)) begin
					next_irq_pending[irq_buserror] = 1;
				end else begin
					cpu_state <= cpu_state_trap;
				end
			end
			if (mem_wordsizeVoted == 1 && reg_op1Voted[0] != 0) begin
				// `debug($display("MISALIGNED HALFWORD: 0x%08x", reg_op1Voted);)
				if (ENABLE_IRQ && (!irq_maskVoted[irq_buserror]) && (!irq_activeVoted)) begin
					next_irq_pending[irq_buserror] = 1;
				end else begin
					cpu_state <= cpu_state_trap;
				end
			end
		end
		if (CATCH_MISALIGN && rstn && mem_do_rinstVoted && (COMPRESSED_ISA ? reg_pcVoted[0] : |reg_pcVoted[1:0])) begin
			// `debug($display("MISALIGNED INSTRUCTION: 0x%08x", reg_pcVoted);)
			if (ENABLE_IRQ && (!irq_maskVoted[irq_buserror]) && (!irq_activeVoted)) begin
				next_irq_pending[irq_buserror] = 1;
			end else begin
				cpu_state <= cpu_state_trap;
			end
		end
		if (!CATCH_ILLINSN && decoder_trigger_q && (!decoder_pseudo_trigger_q) && instr_ecall_ebreak) begin
			cpu_state <= cpu_state_trap;
		end

		if (!rstn || mem_done) begin
			mem_do_prefetch <= 0;
			mem_do_rinst <= 0;
			mem_do_rdata <= 0;
			mem_do_wdata <= 0;
		end

		if (set_mem_do_rinst)
			mem_do_rinst <= 1;
		if (set_mem_do_rdata)
			mem_do_rdata <= 1;
		if (set_mem_do_wdata)
			mem_do_wdata <= 1;

		irq_pending <= next_irq_pending & ~MASKED_IRQ;

		if (!CATCH_MISALIGN) begin
			if (COMPRESSED_ISA) begin
				reg_pc[0] <= 0;
				reg_next_pc[0] <= 0;
			end else begin
				reg_pc[1:0] <= 0;
				reg_next_pc[1:0] <= 0;
			end
		end
		current_pc = 'bx;
	end
	// CPU STATE MACHINE>
	// -----------------------------------

endmodule
