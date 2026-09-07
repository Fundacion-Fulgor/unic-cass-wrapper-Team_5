//=============================================================================
// Updated: 2026-09-01
// Debug register file. Exposes the probe buses as a read-only address map and
// latches the sys_config write. Probes are frozen by a snapshot taken on the
// falling edge of the chip select, writes commit on its rising edge.
//=============================================================================

module debug_unit #(
    parameter NB_ADDR = 7,
    parameter NB_DATA = 8
) (
    `ifdef USE_POWER_PINS
    inout                      VPWR,
    inout                      VGND,
    `endif
    output reg [NB_DATA-1:0]   o_spi_rdata,
    output reg [2:0]           o_sys_config,
    input                      i_clk,
    input                      i_rstn,
    input      [NB_ADDR-1:0]   i_spi_addr,
    input      [NB_DATA-1:0]   i_spi_wdata,
    input                      i_spi_rw,
    input                      i_spi_ss_n,
    input      [NB_DATA-1:0]   i_status_flags,
    input      [NB_DATA-1:0]   i_error_flags,
    input      [NB_DATA-1:0]   i_cnt_inputs,
    input      [NB_DATA-1:0]   i_cnt_outputs,
    input      [NB_DATA-1:0]   i_last_out_re,
    input      [NB_DATA-1:0]   i_last_out_im,
    input      [NB_DATA-1:0]   i_mid_data_re
);

localparam [NB_ADDR-1:0] ADDR_STATUS_FLAGS = 'h00;
localparam [NB_ADDR-1:0] ADDR_ERROR_FLAGS  = 'h01;
localparam [NB_ADDR-1:0] ADDR_CNT_INPUTS   = 'h02;
localparam [NB_ADDR-1:0] ADDR_CNT_OUTPUTS  = 'h03;
localparam [NB_ADDR-1:0] ADDR_LAST_OUT_RE  = 'h04;
localparam [NB_ADDR-1:0] ADDR_LAST_OUT_IM  = 'h05;
localparam [NB_ADDR-1:0] ADDR_MID_DATA_RE  = 'h06;
localparam [NB_ADDR-1:0] ADDR_SYS_CONFIG   = 'h10;

reg  [2:0]         ss_sync;
wire               commit_pulse;

reg  [NB_DATA-1:0] wdata_snap;
reg  [NB_ADDR-1:0] addr_snap;
reg                rw_snap;
reg                commit_pulse_d;

wire [NB_DATA-1:0] status_flags_snap;
wire [NB_DATA-1:0] error_flags_snap;
wire [NB_DATA-1:0] cnt_inputs_snap;
wire [NB_DATA-1:0] cnt_outputs_snap;
wire [NB_DATA-1:0] last_out_re_snap;
wire [NB_DATA-1:0] last_out_im_snap;
wire [NB_DATA-1:0] mid_data_re_snap;

always @(posedge i_clk) begin
    if (!i_rstn) begin
        ss_sync <= 3'b111;
    end
    else begin
        ss_sync <= {ss_sync[1:0], i_spi_ss_n};
    end
end

assign commit_pulse   = (ss_sync[2] == 1'b0) && (ss_sync[1] == 1'b1);

always @(posedge i_clk) begin
    if (!i_rstn) begin
        wdata_snap <= {NB_DATA{1'b0}};
        addr_snap  <= {NB_ADDR{1'b0}};
        rw_snap    <= 1'b1;
    end
    else if (commit_pulse) begin
        wdata_snap <= i_spi_wdata;
        addr_snap  <= i_spi_addr;
        rw_snap    <= i_spi_rw;
    end
end

always @(posedge i_clk) begin
    if (!i_rstn) begin
        commit_pulse_d <= 1'b0;
    end
    else begin
        commit_pulse_d <= commit_pulse;
    end
end

always @(posedge i_clk) begin
    if (!i_rstn) begin
        o_sys_config <= 3'b000;
    end
    else if (commit_pulse_d && !rw_snap && (addr_snap == ADDR_SYS_CONFIG)) begin
        o_sys_config <= wdata_snap[2:0];
    end
end

cdc_snapshot #(
    .DATA_WIDTH  (NB_DATA)
) u_cdc_status_flags (
    `ifdef USE_POWER_PINS
    .VPWR        (VPWR),
    .VGND        (VGND),
    `endif
    .o_data      (status_flags_snap),
    .i_clk       (i_clk),
    .i_rstn      (i_rstn),
    .i_trigger_n (i_spi_ss_n),
    .i_data      (i_status_flags)
);

cdc_snapshot #(
    .DATA_WIDTH  (NB_DATA)
) u_cdc_error_flags (
    `ifdef USE_POWER_PINS
    .VPWR        (VPWR),
    .VGND        (VGND),
    `endif
    .o_data      (error_flags_snap),
    .i_clk       (i_clk),
    .i_rstn      (i_rstn),
    .i_trigger_n (i_spi_ss_n),
    .i_data      (i_error_flags)
);

cdc_snapshot #(
    .DATA_WIDTH  (NB_DATA)
) u_cdc_cnt_inputs (
    `ifdef USE_POWER_PINS
    .VPWR        (VPWR),
    .VGND        (VGND),
    `endif
    .o_data      (cnt_inputs_snap),
    .i_clk       (i_clk),
    .i_rstn      (i_rstn),
    .i_trigger_n (i_spi_ss_n),
    .i_data      (i_cnt_inputs)
);

cdc_snapshot #(
    .DATA_WIDTH  (NB_DATA)
) u_cdc_cnt_outputs (
    `ifdef USE_POWER_PINS
    .VPWR        (VPWR),
    .VGND        (VGND),
    `endif
    .o_data      (cnt_outputs_snap),
    .i_clk       (i_clk),
    .i_rstn      (i_rstn),
    .i_trigger_n (i_spi_ss_n),
    .i_data      (i_cnt_outputs)
);

cdc_snapshot #(
    .DATA_WIDTH  (NB_DATA)
) u_cdc_last_out_re (
    `ifdef USE_POWER_PINS
    .VPWR        (VPWR),
    .VGND        (VGND),
    `endif
    .o_data      (last_out_re_snap),
    .i_clk       (i_clk),
    .i_rstn      (i_rstn),
    .i_trigger_n (i_spi_ss_n),
    .i_data      (i_last_out_re)
);

cdc_snapshot #(
    .DATA_WIDTH  (NB_DATA)
) u_cdc_last_out_im (
    `ifdef USE_POWER_PINS
    .VPWR        (VPWR),
    .VGND        (VGND),
    `endif
    .o_data      (last_out_im_snap),
    .i_clk       (i_clk),
    .i_rstn      (i_rstn),
    .i_trigger_n (i_spi_ss_n),
    .i_data      (i_last_out_im)
);

cdc_snapshot #(
    .DATA_WIDTH  (NB_DATA)
) u_cdc_mid_data_re (
    `ifdef USE_POWER_PINS
    .VPWR        (VPWR),
    .VGND        (VGND),
    `endif
    .o_data      (mid_data_re_snap),
    .i_clk       (i_clk),
    .i_rstn      (i_rstn),
    .i_trigger_n (i_spi_ss_n),
    .i_data      (i_mid_data_re)
);

always @(*) begin
    case (i_spi_addr)
        ADDR_STATUS_FLAGS: o_spi_rdata = status_flags_snap;
        ADDR_ERROR_FLAGS:  o_spi_rdata = error_flags_snap;
        ADDR_CNT_INPUTS:   o_spi_rdata = cnt_inputs_snap;
        ADDR_CNT_OUTPUTS:  o_spi_rdata = cnt_outputs_snap;
        ADDR_LAST_OUT_RE:  o_spi_rdata = last_out_re_snap;
        ADDR_LAST_OUT_IM:  o_spi_rdata = last_out_im_snap;
        ADDR_MID_DATA_RE:  o_spi_rdata = mid_data_re_snap;
        ADDR_SYS_CONFIG:   o_spi_rdata = {{(NB_DATA-3){1'b0}}, o_sys_config};
        default:           o_spi_rdata = {NB_DATA{1'b0}};
    endcase
end

endmodule
