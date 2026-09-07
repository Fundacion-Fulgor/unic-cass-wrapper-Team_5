//=============================================================================
// Updated: 2026-09-01
// Debug subsystem. Wires the SPI slave to the debug register file so an
// external master can read the probe registers and write sys_config.
//=============================================================================

module debug_system (
    `ifdef USE_POWER_PINS
    inout        VPWR,
    inout        VGND,
    `endif
    output       o_miso,
    output [2:0] o_sys_config,
    input        i_clk,
    input        i_rstn,
    input        i_ss_n,
    input        i_sclk,
    input        i_mosi,
    input  [7:0] i_status_flags,
    input  [7:0] i_error_flags,
    input  [7:0] i_cnt_inputs,
    input  [7:0] i_cnt_outputs,
    input  [7:0] i_last_out_re,
    input  [7:0] i_last_out_im,
    input  [7:0] i_mid_data_re
);

wire [6:0]  spi_addr;
wire [7:0]  spi_wdata;
wire        spi_rw;
wire [7:0]  spi_rdata;
wire        spi_write_enable;
wire        spi_done;
wire [15:0] spi_rx_frame;

spi_slave_mode0 #(
    .FRAME_BITS     (16),
    .ADDR_BITS      (7),
    .DATA_BITS      (8)
) u_spi_slave_mode0 (
    `ifdef USE_POWER_PINS
    .VPWR           (VPWR),
    .VGND           (VGND),
    `endif
    .o_miso         (o_miso),
    .o_addr         (spi_addr),
    .o_data         (spi_wdata),
    .o_write_enable (spi_write_enable),
    .o_rw_bit       (spi_rw),
    .o_done         (spi_done),
    .o_rx_frame     (spi_rx_frame),
    .i_rstn         (i_rstn),
    .i_ss_n         (i_ss_n),
    .i_sclk         (i_sclk),
    .i_mosi         (i_mosi),
    .i_data         (spi_rdata)
);

debug_unit #(
    .NB_ADDR        (7),
    .NB_DATA        (8)
) u_debug_unit (
    `ifdef USE_POWER_PINS
    .VPWR           (VPWR),
    .VGND           (VGND),
    `endif
    .o_spi_rdata    (spi_rdata),
    .o_sys_config   (o_sys_config),
    .i_clk          (i_clk),
    .i_rstn         (i_rstn),
    .i_spi_addr     (spi_addr),
    .i_spi_wdata    (spi_wdata),
    .i_spi_rw       (spi_rw),
    .i_spi_ss_n     (i_ss_n),
    .i_status_flags (i_status_flags),
    .i_error_flags  (i_error_flags),
    .i_cnt_inputs   (i_cnt_inputs),
    .i_cnt_outputs  (i_cnt_outputs),
    .i_last_out_re  (i_last_out_re),
    .i_last_out_im  (i_last_out_im),
    .i_mid_data_re  (i_mid_data_re)
);

wire _unused = spi_done ^ spi_write_enable ^ ^spi_rx_frame;

endmodule
