//=============================================================================
// Updated: 2026-09-01
// FFT16 chip top level. Joins the serial input and output links, the FFT core
// and the SPI debug subsystem, and derives the soft reset and the enable and
// inverse controls from the configuration register.
//=============================================================================

module top_fft16 #(
    parameter NB_DATA = 8
) (
    `ifdef USE_POWER_PINS
    inout       VPWR,
    inout       VGND,
    `endif
    output wire o_data,
    output wire o_spi_miso,
    input  wire i_clk,
    input  wire i_rstn,
    input  wire i_data,
    input  wire i_spi_ss_n,
    input  wire i_spi_sclk,
    input  wire i_spi_mosi
);

localparam signed [NB_DATA-1:0] SAT_MAX = {1'b0, {NB_DATA-1{1'b1}}};
localparam signed [NB_DATA-1:0] SAT_MIN = {1'b1, {NB_DATA-1{1'b0}}};

wire [2:0]                sys_config;
wire                      fft_en;
wire                      fft_inverse;
wire                      soft_reset;
wire                      rstn;

wire signed [NB_DATA-1:0] rx_data_re;
wire signed [NB_DATA-1:0] rx_data_im;
wire                      rx_valid;

wire signed [NB_DATA-1:0] fft_out_re;
wire signed [NB_DATA-1:0] fft_out_im;
wire                      fft_out_valid;
wire                      tx_ready;

wire signed [NB_DATA-1:0] debug_mid_re;
wire [NB_DATA-1:0]        status_flags;
wire                      is_clipped;

reg  [NB_DATA-1:0]        cnt_inputs;
reg  [NB_DATA-1:0]        cnt_outputs;
reg  [NB_DATA-1:0]        error_flags;
reg  [NB_DATA-1:0]        last_out_re;
reg  [NB_DATA-1:0]        last_out_im;

assign fft_en      = sys_config[0];
assign fft_inverse = sys_config[1];
assign soft_reset  = sys_config[2];
assign rstn        = i_rstn & (~soft_reset);

rx_serializer #(
    .NB_DATA        (NB_DATA)
) u_rx_serializer (
    `ifdef USE_POWER_PINS
    .VPWR           (VPWR),
    .VGND           (VGND),
    `endif
    .o_data_re      (rx_data_re),
    .o_data_im      (rx_data_im),
    .o_valid        (rx_valid),
    .i_clk          (i_clk),
    .i_rstn         (rstn),
    .i_data         (i_data)
);

fft16 #(
    .NB_DATA        (NB_DATA)
) u_fft16 (
    `ifdef USE_POWER_PINS
    .VPWR           (VPWR),
    .VGND           (VGND),
    `endif
    .o_valid        (fft_out_valid),
    .o_data_re      (fft_out_re),
    .o_data_im      (fft_out_im),
    .o_debug_mid_re (debug_mid_re),
    .i_clk          (i_clk),
    .i_rstn         (rstn),
    .i_en           (fft_en),
    .i_inverse      (fft_inverse),
    .i_valid        (rx_valid),
    .i_tx_ready     (tx_ready),
    .i_data_re      (rx_data_re),
    .i_data_im      (rx_data_im)
);

tx_serializer #(
    .NB_DATA        (NB_DATA)
) u_tx_serializer (
    `ifdef USE_POWER_PINS
    .VPWR           (VPWR),
    .VGND           (VGND),
    `endif
    .o_data         (o_data),
    .o_ready        (tx_ready),
    .i_clk          (i_clk),
    .i_rstn         (rstn),
    .i_valid        (fft_out_valid),
    .i_data_re      (fft_out_re),
    .i_data_im      (fft_out_im)
);

always @(posedge i_clk) begin
    if (!rstn) begin
        cnt_inputs  <= {NB_DATA{1'b0}};
        cnt_outputs <= {NB_DATA{1'b0}};
    end
    else begin
        if (rx_valid) begin
            cnt_inputs <= cnt_inputs + 1'b1;
        end
        if (fft_out_valid) begin
            cnt_outputs <= cnt_outputs + 1'b1;
        end
    end
end

assign status_flags = {{(NB_DATA-4){1'b0}}, fft_inverse, tx_ready, fft_out_valid, rx_valid};

assign is_clipped = (fft_out_re == SAT_MAX) || (fft_out_re == SAT_MIN) ||
                    (fft_out_im == SAT_MAX) || (fft_out_im == SAT_MIN);

always @(posedge i_clk) begin
    if (!rstn) begin
        error_flags <= {NB_DATA{1'b0}};
    end
    else if (fft_out_valid && is_clipped) begin
        error_flags[0] <= 1'b1;
    end
end

always @(posedge i_clk) begin
    if (!rstn) begin
        last_out_re <= {NB_DATA{1'b0}};
        last_out_im <= {NB_DATA{1'b0}};
    end
    else if (fft_out_valid) begin
        last_out_re <= fft_out_re;
        last_out_im <= fft_out_im;
    end
end

debug_system u_debug_system (
    `ifdef USE_POWER_PINS
    .VPWR           (VPWR),
    .VGND           (VGND),
    `endif
    .o_miso         (o_spi_miso),
    .o_sys_config   (sys_config),
    .i_clk          (i_clk),
    .i_rstn         (i_rstn),
    .i_ss_n         (i_spi_ss_n),
    .i_sclk         (i_spi_sclk),
    .i_mosi         (i_spi_mosi),
    .i_status_flags (status_flags),
    .i_error_flags  (error_flags),
    .i_cnt_inputs   (cnt_inputs),
    .i_cnt_outputs  (cnt_outputs),
    .i_last_out_re  (last_out_re),
    .i_last_out_im  (last_out_im),
    .i_mid_data_re  (debug_mid_re)
);

endmodule
