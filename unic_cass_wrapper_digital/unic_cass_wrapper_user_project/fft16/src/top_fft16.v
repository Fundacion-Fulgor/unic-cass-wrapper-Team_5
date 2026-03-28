module top_fft16 #(
    parameter NB_DATA = 8
) (
    `ifdef USE_POWER_PINS
    inout       VPWR,
    inout       VGND,
    `endif
    output wire o_data,
    output wire o_spi_miso,
    input  wire i_data,
    input  wire i_spi_ss_n,
    input  wire i_spi_sclk,
    input  wire i_spi_mosi,
    input  wire i_clk,
    input  wire i_rst_n
);

wire [2:0] sys_config;
wire       fft_enable;
wire       fft_inverse;
wire       soft_reset;
wire       rst_n;

wire signed [NB_DATA-1:0] rx_data_re, rx_data_im;
wire                      rx_valid;

wire signed [NB_DATA-1:0] fft_out_re, fft_out_im;
wire                      fft_out_valid;
wire                      tx_ready;

wire signed [NB_DATA-1:0] debug_mid_data_re;

assign fft_enable  = sys_config[0];
assign fft_inverse = sys_config[1];
assign soft_reset  = sys_config[2];
assign rst_n       = i_rst_n & (~soft_reset);

rx_serializer #( .NB_DATA(NB_DATA) ) u_rx (
    `ifdef USE_POWER_PINS
    .VPWR      (VPWR),
    .VGND      (VGND),
    `endif
    .i_clk     (i_clk),
    .i_rst_n   (rst_n),
    .i_data    (i_data),
    .o_data_re (rx_data_re),
    .o_data_im (rx_data_im),
    .o_valid   (rx_valid)
);

fft16 #( .NB_DATA(NB_DATA) ) u_fft_core (
    `ifdef USE_POWER_PINS
    .VPWR           (VPWR),
    .VGND           (VGND),
    `endif
    .i_clk          (i_clk),
    .i_clk_en       (fft_enable),
    .i_rst_n        (rst_n),
    .i_inverse      (fft_inverse),
    .i_valid        (rx_valid),
    .i_tx_ready     (tx_ready),
    .i_data_re      (rx_data_re),
    .i_data_im      (rx_data_im),
    .o_valid        (fft_out_valid),
    .o_data_re      (fft_out_re),
    .o_data_im      (fft_out_im),
    .o_debug_mid_re (debug_mid_data_re)
);

tx_serializer #( .NB_DATA(NB_DATA) ) u_tx (
    `ifdef USE_POWER_PINS
    .VPWR      (VPWR),
    .VGND      (VGND),
    `endif
    .i_clk     (i_clk),
    .i_rst_n   (rst_n),
    .i_valid   (fft_out_valid),
    .i_data_re (fft_out_re),
    .i_data_im (fft_out_im),
    .o_data    (o_data),
    .o_ready   (tx_ready)
);

reg [NB_DATA-1:0] cnt_inputs;
reg [NB_DATA-1:0] cnt_outputs;

always @(posedge i_clk or negedge rst_n) begin
    if (!rst_n) begin
        cnt_inputs  <= 0;
        cnt_outputs <= 0;
    end
    else begin
        if (rx_valid)      cnt_inputs  <= cnt_inputs  + 1'b1;
        if (fft_out_valid) cnt_outputs <= cnt_outputs + 1'b1;
    end
end

wire [NB_DATA-1:0] status_flags;
assign status_flags = {4'b0, fft_inverse, tx_ready, fft_out_valid, rx_valid};

reg [NB_DATA-1:0] error_flags;
wire              is_clipped;

assign is_clipped = (fft_out_re == 8'h7F) || (fft_out_re == 8'h80) ||
                    (fft_out_im == 8'h7F) || (fft_out_im == 8'h80);

always @(posedge i_clk or negedge rst_n) begin
    if (!rst_n)
        error_flags <= 0;
    else if (fft_out_valid && is_clipped)
        error_flags[0] <= 1'b1;
end

reg [NB_DATA-1:0] last_out_re;
reg [NB_DATA-1:0] last_out_im;

always @(posedge i_clk or negedge rst_n) begin
    if (!rst_n) begin
        last_out_re <= 0;
        last_out_im <= 0;
    end
    else if (fft_out_valid) begin
        last_out_re <= fft_out_re;
        last_out_im <= fft_out_im;
    end
end

debug_system u_debug_sys (
    `ifdef USE_POWER_PINS
    .VPWR         (VPWR),
    .VGND         (VGND),
    `endif
    .clk          (i_clk),
    .rst_n        (i_rst_n),
    .ss_n         (i_spi_ss_n),
    .sclk         (i_spi_sclk),
    .mosi         (i_spi_mosi),
    .miso         (o_spi_miso),
    .status_flags (status_flags),
    .error_flags  (error_flags),
    .cnt_inputs   (cnt_inputs),
    .cnt_outputs  (cnt_outputs),
    .last_out_re  (last_out_re),
    .last_out_im  (last_out_im),
    .mid_data_re  (debug_mid_data_re),
    .sys_config   (sys_config)
);

endmodule