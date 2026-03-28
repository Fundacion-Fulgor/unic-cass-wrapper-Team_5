module debug_system (
    `ifdef USE_POWER_PINS
    inout        VPWR,
    inout        VGND,
    `endif
    input        clk,
    input        rst_n,
    input        ss_n,
    input        sclk,
    input        mosi,
    input  [7:0] status_flags,
    input  [7:0] error_flags,
    input  [7:0] cnt_inputs,
    input  [7:0] cnt_outputs,
    input  [7:0] last_out_re,
    input  [7:0] last_out_im,
    input  [7:0] mid_data_re,
    output [2:0] sys_config,
    output       miso
);

wire [6:0]  addr_out;
wire [7:0]  data_to_dut;
wire        rw_bit;
wire [7:0]  data_from_dut;
wire        spi_done;
wire [15:0] spi_rx_frame;

spi_slave_mode0 #(
    .FRAME_BITS (16),
    .ADDR_BITS  (7),
    .DATA_BITS  (8)
) u_spi_slave (
    `ifdef USE_POWER_PINS
    .VPWR         (VPWR),
    .VGND         (VGND),
    `endif
    .rst_n        (rst_n),
    .ss_n         (ss_n),
    .sclk         (sclk),
    .mosi         (mosi),
    .miso         (miso),
    .addr_out     (addr_out),
    .data_out     (data_to_dut),
    .write_enable (),          // no longer used by debug_unit
    .rw_bit       (rw_bit),
    .data_in      (data_from_dut),
    .done         (spi_done),
    .rx_frame     (spi_rx_frame)
);

wire _unused_spi = spi_done ^ ^spi_rx_frame;

debug_unit #(
    .NB_ADDR (7),
    .NB_DATA (8)
) u_debug_unit (
    `ifdef USE_POWER_PINS
    .VPWR         (VPWR),
    .VGND         (VGND),
    `endif
    .clk          (clk),
    .rst_n        (rst_n),
    .spi_addr     (addr_out),
    .spi_wdata    (data_to_dut),
    .spi_rw       (rw_bit),
    .spi_rdata    (data_from_dut),
    .spi_ss_n     (ss_n),
    .status_flags (status_flags),
    .error_flags  (error_flags),
    .cnt_inputs   (cnt_inputs),
    .cnt_outputs  (cnt_outputs),
    .last_out_re  (last_out_re),
    .last_out_im  (last_out_im),
    .mid_data_re  (mid_data_re),
    .sys_config   (sys_config)
);

endmodule