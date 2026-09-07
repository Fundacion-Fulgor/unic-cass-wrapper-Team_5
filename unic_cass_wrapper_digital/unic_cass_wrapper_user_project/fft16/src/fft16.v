//=============================================================================
// Updated: 2026-09-01
// Mixed-radix FFT16 core. A radix-4 stage with twiddle multipliers feeds four
// parallel radix-2 MDC pipelines, one per output group. The results are
// rescaled for the forward or the inverse transform and pushed into the
// output frame buffer.
//=============================================================================

module fft16 #(
    parameter NB_DATA = 8
) (
    `ifdef USE_POWER_PINS
    inout                       VPWR,
    inout                       VGND,
    `endif
    output                      o_valid,
    output signed [NB_DATA-1:0] o_data_re,
    output signed [NB_DATA-1:0] o_data_im,
    output signed [NB_DATA-1:0] o_debug_mid_re,
    input                       i_clk,
    input                       i_rstn,
    input                       i_en,
    input                       i_inverse,
    input                       i_valid,
    input                       i_tx_ready,
    input  signed [NB_DATA-1:0] i_data_re,
    input  signed [NB_DATA-1:0] i_data_im
);

reg                       inv_d;
reg                       mdc_valid_d;

wire signed [NB_DATA-1:0] shift_r4_data0_re;
wire signed [NB_DATA-1:0] shift_r4_data0_im;
wire signed [NB_DATA-1:0] shift_r4_data1_re;
wire signed [NB_DATA-1:0] shift_r4_data1_im;
wire signed [NB_DATA-1:0] shift_r4_data2_re;
wire signed [NB_DATA-1:0] shift_r4_data2_im;
wire signed [NB_DATA-1:0] shift_r4_data3_re;
wire signed [NB_DATA-1:0] shift_r4_data3_im;
wire                      shift_r4_valid;

wire signed [NB_DATA+1:0] fft4_data0_re;
wire signed [NB_DATA+1:0] fft4_data0_im;
wire signed [NB_DATA+1:0] fft4_data1_re;
wire signed [NB_DATA+1:0] fft4_data1_im;
wire signed [NB_DATA+1:0] fft4_data2_re;
wire signed [NB_DATA+1:0] fft4_data2_im;
wire signed [NB_DATA+1:0] fft4_data3_re;
wire signed [NB_DATA+1:0] fft4_data3_im;
wire                      fft4_valid;

wire signed [NB_DATA+1:0] shift_r2_ff0_data0_re;
wire signed [NB_DATA+1:0] shift_r2_ff0_data0_im;
wire signed [NB_DATA+1:0] shift_r2_ff0_data1_re;
wire signed [NB_DATA+1:0] shift_r2_ff0_data1_im;
wire signed [NB_DATA+1:0] shift_r2_ff1_data0_re;
wire signed [NB_DATA+1:0] shift_r2_ff1_data0_im;
wire signed [NB_DATA+1:0] shift_r2_ff1_data1_re;
wire signed [NB_DATA+1:0] shift_r2_ff1_data1_im;
wire signed [NB_DATA+1:0] shift_r2_ff2_data0_re;
wire signed [NB_DATA+1:0] shift_r2_ff2_data0_im;
wire signed [NB_DATA+1:0] shift_r2_ff2_data1_re;
wire signed [NB_DATA+1:0] shift_r2_ff2_data1_im;
wire signed [NB_DATA+1:0] shift_r2_ff3_data0_re;
wire signed [NB_DATA+1:0] shift_r2_ff3_data0_im;
wire signed [NB_DATA+1:0] shift_r2_ff3_data1_re;
wire signed [NB_DATA+1:0] shift_r2_ff3_data1_im;

wire                      shift_r2_ff0_valid;
wire                      shift_r2_ff1_valid;
wire                      shift_r2_ff2_valid;
wire                      shift_r2_ff3_valid;

wire signed [NB_DATA+3:0] mdc_ff0_data0_re;
wire signed [NB_DATA+3:0] mdc_ff0_data0_im;
wire signed [NB_DATA+3:0] mdc_ff0_data1_re;
wire signed [NB_DATA+3:0] mdc_ff0_data1_im;
wire signed [NB_DATA+3:0] mdc_ff1_data0_re;
wire signed [NB_DATA+3:0] mdc_ff1_data0_im;
wire signed [NB_DATA+3:0] mdc_ff1_data1_re;
wire signed [NB_DATA+3:0] mdc_ff1_data1_im;
wire signed [NB_DATA+3:0] mdc_ff2_data0_re;
wire signed [NB_DATA+3:0] mdc_ff2_data0_im;
wire signed [NB_DATA+3:0] mdc_ff2_data1_re;
wire signed [NB_DATA+3:0] mdc_ff2_data1_im;
wire signed [NB_DATA+3:0] mdc_ff3_data0_re;
wire signed [NB_DATA+3:0] mdc_ff3_data0_im;
wire signed [NB_DATA+3:0] mdc_ff3_data1_re;
wire signed [NB_DATA+3:0] mdc_ff3_data1_im;

wire                      mdc_ff0_valid;
wire                      mdc_ff1_valid;
wire                      mdc_ff2_valid;
wire                      mdc_ff3_valid;
wire                      mdc_ffx_valid;

wire signed [NB_DATA-1:0] rnd_mdc0_x0_re;
wire signed [NB_DATA-1:0] rnd_mdc0_x0_im;
wire signed [NB_DATA-1:0] rnd_mdc0_x1_re;
wire signed [NB_DATA-1:0] rnd_mdc0_x1_im;
wire signed [NB_DATA-1:0] rnd_mdc1_x0_re;
wire signed [NB_DATA-1:0] rnd_mdc1_x0_im;
wire signed [NB_DATA-1:0] rnd_mdc1_x1_re;
wire signed [NB_DATA-1:0] rnd_mdc1_x1_im;
wire signed [NB_DATA-1:0] rnd_mdc2_x0_re;
wire signed [NB_DATA-1:0] rnd_mdc2_x0_im;
wire signed [NB_DATA-1:0] rnd_mdc2_x1_re;
wire signed [NB_DATA-1:0] rnd_mdc2_x1_im;
wire signed [NB_DATA-1:0] rnd_mdc3_x0_re;
wire signed [NB_DATA-1:0] rnd_mdc3_x0_im;
wire signed [NB_DATA-1:0] rnd_mdc3_x1_re;
wire signed [NB_DATA-1:0] rnd_mdc3_x1_im;

wire signed [NB_DATA-1:0] rnd_ifft0_x0_re;
wire signed [NB_DATA-1:0] rnd_ifft0_x0_im;
wire signed [NB_DATA-1:0] rnd_ifft0_x1_re;
wire signed [NB_DATA-1:0] rnd_ifft0_x1_im;
wire signed [NB_DATA-1:0] rnd_ifft1_x0_re;
wire signed [NB_DATA-1:0] rnd_ifft1_x0_im;
wire signed [NB_DATA-1:0] rnd_ifft1_x1_re;
wire signed [NB_DATA-1:0] rnd_ifft1_x1_im;
wire signed [NB_DATA-1:0] rnd_ifft2_x0_re;
wire signed [NB_DATA-1:0] rnd_ifft2_x0_im;
wire signed [NB_DATA-1:0] rnd_ifft2_x1_re;
wire signed [NB_DATA-1:0] rnd_ifft2_x1_im;
wire signed [NB_DATA-1:0] rnd_ifft3_x0_re;
wire signed [NB_DATA-1:0] rnd_ifft3_x0_im;
wire signed [NB_DATA-1:0] rnd_ifft3_x1_re;
wire signed [NB_DATA-1:0] rnd_ifft3_x1_im;

reg  signed [NB_DATA-1:0] buffer0_re;
reg  signed [NB_DATA-1:0] buffer0_im;
reg  signed [NB_DATA-1:0] buffer1_re;
reg  signed [NB_DATA-1:0] buffer1_im;
reg  signed [NB_DATA-1:0] buffer2_re;
reg  signed [NB_DATA-1:0] buffer2_im;
reg  signed [NB_DATA-1:0] buffer3_re;
reg  signed [NB_DATA-1:0] buffer3_im;
reg  signed [NB_DATA-1:0] buffer4_re;
reg  signed [NB_DATA-1:0] buffer4_im;
reg  signed [NB_DATA-1:0] buffer5_re;
reg  signed [NB_DATA-1:0] buffer5_im;
reg  signed [NB_DATA-1:0] buffer6_re;
reg  signed [NB_DATA-1:0] buffer6_im;
reg  signed [NB_DATA-1:0] buffer7_re;
reg  signed [NB_DATA-1:0] buffer7_im;

always @(posedge i_clk) begin
    inv_d <= i_inverse;
end

fft16_shift_r4 #(
    .NB_DATA    (NB_DATA)
) u_fft16_shift_r4 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .o_data0_re (shift_r4_data0_re),
    .o_data0_im (shift_r4_data0_im),
    .o_data1_re (shift_r4_data1_re),
    .o_data1_im (shift_r4_data1_im),
    .o_data2_re (shift_r4_data2_re),
    .o_data2_im (shift_r4_data2_im),
    .o_data3_re (shift_r4_data3_re),
    .o_data3_im (shift_r4_data3_im),
    .o_valid    (shift_r4_valid),
    .i_clk      (i_clk),
    .i_rstn     (i_rstn),
    .i_en       (i_en),
    .i_valid    (i_valid),
    .i_data_re  (i_data_re),
    .i_data_im  (i_data_im)
);

fft4_radix4 #(
    .NB_INPUT   (NB_DATA)
) u_fft4_radix4 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .o_valid    (fft4_valid),
    .o_data0_re (fft4_data0_re),
    .o_data0_im (fft4_data0_im),
    .o_data1_re (fft4_data1_re),
    .o_data1_im (fft4_data1_im),
    .o_data2_re (fft4_data2_re),
    .o_data2_im (fft4_data2_im),
    .o_data3_re (fft4_data3_re),
    .o_data3_im (fft4_data3_im),
    .i_clk      (i_clk),
    .i_rstn     (i_rstn),
    .i_en       (i_en),
    .i_inverse  (inv_d),
    .i_valid    (shift_r4_valid),
    .i_data0_re (shift_r4_data0_re),
    .i_data0_im (shift_r4_data0_im),
    .i_data1_re (shift_r4_data1_re),
    .i_data1_im (shift_r4_data1_im),
    .i_data2_re (shift_r4_data2_re),
    .i_data2_im (shift_r4_data2_im),
    .i_data3_re (shift_r4_data3_re),
    .i_data3_im (shift_r4_data3_im)
);

fft16_shift_r2 #(
    .NB_DATA    (NB_DATA+2)
) u_fft16_shift_r2_0 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .o_data0_re (shift_r2_ff0_data0_re),
    .o_data0_im (shift_r2_ff0_data0_im),
    .o_data1_re (shift_r2_ff0_data1_re),
    .o_data1_im (shift_r2_ff0_data1_im),
    .o_valid    (shift_r2_ff0_valid),
    .i_clk      (i_clk),
    .i_rstn     (i_rstn),
    .i_en       (i_en),
    .i_valid    (fft4_valid),
    .i_data_re  (fft4_data0_re),
    .i_data_im  (fft4_data0_im)
);

fft16_shift_r2 #(
    .NB_DATA    (NB_DATA+2)
) u_fft16_shift_r2_1 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .o_data0_re (shift_r2_ff1_data0_re),
    .o_data0_im (shift_r2_ff1_data0_im),
    .o_data1_re (shift_r2_ff1_data1_re),
    .o_data1_im (shift_r2_ff1_data1_im),
    .o_valid    (shift_r2_ff1_valid),
    .i_clk      (i_clk),
    .i_rstn     (i_rstn),
    .i_en       (i_en),
    .i_valid    (fft4_valid),
    .i_data_re  (fft4_data1_re),
    .i_data_im  (fft4_data1_im)
);

fft16_shift_r2 #(
    .NB_DATA    (NB_DATA+2)
) u_fft16_shift_r2_2 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .o_data0_re (shift_r2_ff2_data0_re),
    .o_data0_im (shift_r2_ff2_data0_im),
    .o_data1_re (shift_r2_ff2_data1_re),
    .o_data1_im (shift_r2_ff2_data1_im),
    .o_valid    (shift_r2_ff2_valid),
    .i_clk      (i_clk),
    .i_rstn     (i_rstn),
    .i_en       (i_en),
    .i_valid    (fft4_valid),
    .i_data_re  (fft4_data2_re),
    .i_data_im  (fft4_data2_im)
);

fft16_shift_r2 #(
    .NB_DATA    (NB_DATA+2)
) u_fft16_shift_r2_3 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .o_data0_re (shift_r2_ff3_data0_re),
    .o_data0_im (shift_r2_ff3_data0_im),
    .o_data1_re (shift_r2_ff3_data1_re),
    .o_data1_im (shift_r2_ff3_data1_im),
    .o_valid    (shift_r2_ff3_valid),
    .i_clk      (i_clk),
    .i_rstn     (i_rstn),
    .i_en       (i_en),
    .i_valid    (fft4_valid),
    .i_data_re  (fft4_data3_re),
    .i_data_im  (fft4_data3_im)
);

fft4_mdc #(
    .NB_INPUT   (NB_DATA+2)
) u_fft4_mdc_0 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .o_valid    (mdc_ff0_valid),
    .o_data1_r  (mdc_ff0_data0_re),
    .o_data1_i  (mdc_ff0_data0_im),
    .o_data2_r  (mdc_ff0_data1_re),
    .o_data2_i  (mdc_ff0_data1_im),
    .i_clk      (i_clk),
    .i_rstn     (i_rstn),
    .i_inverse  (inv_d),
    .i_valid    (shift_r2_ff0_valid),
    .i_data1_r  (shift_r2_ff0_data0_re),
    .i_data1_i  (shift_r2_ff0_data0_im),
    .i_data2_r  (shift_r2_ff0_data1_re),
    .i_data2_i  (shift_r2_ff0_data1_im)
);

fft4_mdc #(
    .NB_INPUT   (NB_DATA+2)
) u_fft4_mdc_1 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .o_valid    (mdc_ff1_valid),
    .o_data1_r  (mdc_ff1_data0_re),
    .o_data1_i  (mdc_ff1_data0_im),
    .o_data2_r  (mdc_ff1_data1_re),
    .o_data2_i  (mdc_ff1_data1_im),
    .i_clk      (i_clk),
    .i_rstn     (i_rstn),
    .i_inverse  (inv_d),
    .i_valid    (shift_r2_ff1_valid),
    .i_data1_r  (shift_r2_ff1_data0_re),
    .i_data1_i  (shift_r2_ff1_data0_im),
    .i_data2_r  (shift_r2_ff1_data1_re),
    .i_data2_i  (shift_r2_ff1_data1_im)
);

fft4_mdc #(
    .NB_INPUT   (NB_DATA+2)
) u_fft4_mdc_2 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .o_valid    (mdc_ff2_valid),
    .o_data1_r  (mdc_ff2_data0_re),
    .o_data1_i  (mdc_ff2_data0_im),
    .o_data2_r  (mdc_ff2_data1_re),
    .o_data2_i  (mdc_ff2_data1_im),
    .i_clk      (i_clk),
    .i_rstn     (i_rstn),
    .i_inverse  (inv_d),
    .i_valid    (shift_r2_ff2_valid),
    .i_data1_r  (shift_r2_ff2_data0_re),
    .i_data1_i  (shift_r2_ff2_data0_im),
    .i_data2_r  (shift_r2_ff2_data1_re),
    .i_data2_i  (shift_r2_ff2_data1_im)
);

fft4_mdc #(
    .NB_INPUT   (NB_DATA+2)
) u_fft4_mdc_3 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .o_valid    (mdc_ff3_valid),
    .o_data1_r  (mdc_ff3_data0_re),
    .o_data1_i  (mdc_ff3_data0_im),
    .o_data2_r  (mdc_ff3_data1_re),
    .o_data2_i  (mdc_ff3_data1_im),
    .i_clk      (i_clk),
    .i_rstn     (i_rstn),
    .i_inverse  (inv_d),
    .i_valid    (shift_r2_ff3_valid),
    .i_data1_r  (shift_r2_ff3_data0_re),
    .i_data1_i  (shift_r2_ff3_data0_im),
    .i_data2_r  (shift_r2_ff3_data1_re),
    .i_data2_i  (shift_r2_ff3_data1_im)
);

assign mdc_ffx_valid = mdc_ff0_valid & mdc_ff1_valid & mdc_ff2_valid & mdc_ff3_valid;

clip_round #(
    .NB_INP    (NB_DATA+4),
    .NBF_INP   (NB_DATA-2),
    .NB_OUT    (NB_DATA),
    .NBF_OUT   (NB_DATA-5),
    .RND_MD    (1)
) u_clip_round_mdc0_x0 (
    `ifdef USE_POWER_PINS
    .VPWR      (VPWR),
    .VGND      (VGND),
    `endif
    .o_data_re (rnd_mdc0_x0_re),
    .o_data_im (rnd_mdc0_x0_im),
    .i_data_re (mdc_ff0_data0_re),
    .i_data_im (mdc_ff0_data0_im)
);

clip_round #(
    .NB_INP    (NB_DATA+4),
    .NBF_INP   (NB_DATA-1),
    .NB_OUT    (NB_DATA),
    .NBF_OUT   (NB_DATA-2),
    .RND_MD    (1)
) u_clip_round_ifft0_x0 (
    `ifdef USE_POWER_PINS
    .VPWR      (VPWR),
    .VGND      (VGND),
    `endif
    .o_data_re (rnd_ifft0_x0_re),
    .o_data_im (rnd_ifft0_x0_im),
    .i_data_re (mdc_ff0_data0_re),
    .i_data_im (mdc_ff0_data0_im)
);

clip_round #(
    .NB_INP    (NB_DATA+4),
    .NBF_INP   (NB_DATA-2),
    .NB_OUT    (NB_DATA),
    .NBF_OUT   (NB_DATA-5),
    .RND_MD    (1)
) u_clip_round_mdc0_x1 (
    `ifdef USE_POWER_PINS
    .VPWR      (VPWR),
    .VGND      (VGND),
    `endif
    .o_data_re (rnd_mdc0_x1_re),
    .o_data_im (rnd_mdc0_x1_im),
    .i_data_re (mdc_ff0_data1_re),
    .i_data_im (mdc_ff0_data1_im)
);

clip_round #(
    .NB_INP    (NB_DATA+4),
    .NBF_INP   (NB_DATA-1),
    .NB_OUT    (NB_DATA),
    .NBF_OUT   (NB_DATA-2),
    .RND_MD    (1)
) u_clip_round_ifft0_x1 (
    `ifdef USE_POWER_PINS
    .VPWR      (VPWR),
    .VGND      (VGND),
    `endif
    .o_data_re (rnd_ifft0_x1_re),
    .o_data_im (rnd_ifft0_x1_im),
    .i_data_re (mdc_ff0_data1_re),
    .i_data_im (mdc_ff0_data1_im)
);

clip_round #(
    .NB_INP    (NB_DATA+4),
    .NBF_INP   (NB_DATA-2),
    .NB_OUT    (NB_DATA),
    .NBF_OUT   (NB_DATA-5),
    .RND_MD    (1)
) u_clip_round_mdc1_x0 (
    `ifdef USE_POWER_PINS
    .VPWR      (VPWR),
    .VGND      (VGND),
    `endif
    .o_data_re (rnd_mdc1_x0_re),
    .o_data_im (rnd_mdc1_x0_im),
    .i_data_re (mdc_ff1_data0_re),
    .i_data_im (mdc_ff1_data0_im)
);

clip_round #(
    .NB_INP    (NB_DATA+4),
    .NBF_INP   (NB_DATA-1),
    .NB_OUT    (NB_DATA),
    .NBF_OUT   (NB_DATA-2),
    .RND_MD    (1)
) u_clip_round_ifft1_x0 (
    `ifdef USE_POWER_PINS
    .VPWR      (VPWR),
    .VGND      (VGND),
    `endif
    .o_data_re (rnd_ifft1_x0_re),
    .o_data_im (rnd_ifft1_x0_im),
    .i_data_re (mdc_ff1_data0_re),
    .i_data_im (mdc_ff1_data0_im)
);

clip_round #(
    .NB_INP    (NB_DATA+4),
    .NBF_INP   (NB_DATA-2),
    .NB_OUT    (NB_DATA),
    .NBF_OUT   (NB_DATA-5),
    .RND_MD    (1)
) u_clip_round_mdc1_x1 (
    `ifdef USE_POWER_PINS
    .VPWR      (VPWR),
    .VGND      (VGND),
    `endif
    .o_data_re (rnd_mdc1_x1_re),
    .o_data_im (rnd_mdc1_x1_im),
    .i_data_re (mdc_ff1_data1_re),
    .i_data_im (mdc_ff1_data1_im)
);

clip_round #(
    .NB_INP    (NB_DATA+4),
    .NBF_INP   (NB_DATA-1),
    .NB_OUT    (NB_DATA),
    .NBF_OUT   (NB_DATA-2),
    .RND_MD    (1)
) u_clip_round_ifft1_x1 (
    `ifdef USE_POWER_PINS
    .VPWR      (VPWR),
    .VGND      (VGND),
    `endif
    .o_data_re (rnd_ifft1_x1_re),
    .o_data_im (rnd_ifft1_x1_im),
    .i_data_re (mdc_ff1_data1_re),
    .i_data_im (mdc_ff1_data1_im)
);

clip_round #(
    .NB_INP    (NB_DATA+4),
    .NBF_INP   (NB_DATA-2),
    .NB_OUT    (NB_DATA),
    .NBF_OUT   (NB_DATA-5),
    .RND_MD    (1)
) u_clip_round_mdc2_x0 (
    `ifdef USE_POWER_PINS
    .VPWR      (VPWR),
    .VGND      (VGND),
    `endif
    .o_data_re (rnd_mdc2_x0_re),
    .o_data_im (rnd_mdc2_x0_im),
    .i_data_re (mdc_ff2_data0_re),
    .i_data_im (mdc_ff2_data0_im)
);

clip_round #(
    .NB_INP    (NB_DATA+4),
    .NBF_INP   (NB_DATA-1),
    .NB_OUT    (NB_DATA),
    .NBF_OUT   (NB_DATA-2),
    .RND_MD    (1)
) u_clip_round_ifft2_x0 (
    `ifdef USE_POWER_PINS
    .VPWR      (VPWR),
    .VGND      (VGND),
    `endif
    .o_data_re (rnd_ifft2_x0_re),
    .o_data_im (rnd_ifft2_x0_im),
    .i_data_re (mdc_ff2_data0_re),
    .i_data_im (mdc_ff2_data0_im)
);

clip_round #(
    .NB_INP    (NB_DATA+4),
    .NBF_INP   (NB_DATA-2),
    .NB_OUT    (NB_DATA),
    .NBF_OUT   (NB_DATA-5),
    .RND_MD    (1)
) u_clip_round_mdc2_x1 (
    `ifdef USE_POWER_PINS
    .VPWR      (VPWR),
    .VGND      (VGND),
    `endif
    .o_data_re (rnd_mdc2_x1_re),
    .o_data_im (rnd_mdc2_x1_im),
    .i_data_re (mdc_ff2_data1_re),
    .i_data_im (mdc_ff2_data1_im)
);

clip_round #(
    .NB_INP    (NB_DATA+4),
    .NBF_INP   (NB_DATA-1),
    .NB_OUT    (NB_DATA),
    .NBF_OUT   (NB_DATA-2),
    .RND_MD    (1)
) u_clip_round_ifft2_x1 (
    `ifdef USE_POWER_PINS
    .VPWR      (VPWR),
    .VGND      (VGND),
    `endif
    .o_data_re (rnd_ifft2_x1_re),
    .o_data_im (rnd_ifft2_x1_im),
    .i_data_re (mdc_ff2_data1_re),
    .i_data_im (mdc_ff2_data1_im)
);

clip_round #(
    .NB_INP    (NB_DATA+4),
    .NBF_INP   (NB_DATA-2),
    .NB_OUT    (NB_DATA),
    .NBF_OUT   (NB_DATA-5),
    .RND_MD    (1)
) u_clip_round_mdc3_x0 (
    `ifdef USE_POWER_PINS
    .VPWR      (VPWR),
    .VGND      (VGND),
    `endif
    .o_data_re (rnd_mdc3_x0_re),
    .o_data_im (rnd_mdc3_x0_im),
    .i_data_re (mdc_ff3_data0_re),
    .i_data_im (mdc_ff3_data0_im)
);

clip_round #(
    .NB_INP    (NB_DATA+4),
    .NBF_INP   (NB_DATA-1),
    .NB_OUT    (NB_DATA),
    .NBF_OUT   (NB_DATA-2),
    .RND_MD    (1)
) u_clip_round_ifft3_x0 (
    `ifdef USE_POWER_PINS
    .VPWR      (VPWR),
    .VGND      (VGND),
    `endif
    .o_data_re (rnd_ifft3_x0_re),
    .o_data_im (rnd_ifft3_x0_im),
    .i_data_re (mdc_ff3_data0_re),
    .i_data_im (mdc_ff3_data0_im)
);

clip_round #(
    .NB_INP    (NB_DATA+4),
    .NBF_INP   (NB_DATA-2),
    .NB_OUT    (NB_DATA),
    .NBF_OUT   (NB_DATA-5),
    .RND_MD    (1)
) u_clip_round_mdc3_x1 (
    `ifdef USE_POWER_PINS
    .VPWR      (VPWR),
    .VGND      (VGND),
    `endif
    .o_data_re (rnd_mdc3_x1_re),
    .o_data_im (rnd_mdc3_x1_im),
    .i_data_re (mdc_ff3_data1_re),
    .i_data_im (mdc_ff3_data1_im)
);

clip_round #(
    .NB_INP    (NB_DATA+4),
    .NBF_INP   (NB_DATA-1),
    .NB_OUT    (NB_DATA),
    .NBF_OUT   (NB_DATA-2),
    .RND_MD    (1)
) u_clip_round_ifft3_x1 (
    `ifdef USE_POWER_PINS
    .VPWR      (VPWR),
    .VGND      (VGND),
    `endif
    .o_data_re (rnd_ifft3_x1_re),
    .o_data_im (rnd_ifft3_x1_im),
    .i_data_re (mdc_ff3_data1_re),
    .i_data_im (mdc_ff3_data1_im)
);

always @(posedge i_clk) begin
    mdc_valid_d <= mdc_ffx_valid;
    buffer0_re <= (inv_d) ? rnd_ifft0_x0_re : rnd_mdc0_x0_re;
    buffer0_im <= (inv_d) ? rnd_ifft0_x0_im : rnd_mdc0_x0_im;
    buffer1_re <= (inv_d) ? rnd_ifft0_x1_re : rnd_mdc0_x1_re;
    buffer1_im <= (inv_d) ? rnd_ifft0_x1_im : rnd_mdc0_x1_im;
    buffer2_re <= (inv_d) ? rnd_ifft1_x0_re : rnd_mdc1_x0_re;
    buffer2_im <= (inv_d) ? rnd_ifft1_x0_im : rnd_mdc1_x0_im;
    buffer3_re <= (inv_d) ? rnd_ifft1_x1_re : rnd_mdc1_x1_re;
    buffer3_im <= (inv_d) ? rnd_ifft1_x1_im : rnd_mdc1_x1_im;
    buffer4_re <= (inv_d) ? rnd_ifft2_x0_re : rnd_mdc2_x0_re;
    buffer4_im <= (inv_d) ? rnd_ifft2_x0_im : rnd_mdc2_x0_im;
    buffer5_re <= (inv_d) ? rnd_ifft2_x1_re : rnd_mdc2_x1_re;
    buffer5_im <= (inv_d) ? rnd_ifft2_x1_im : rnd_mdc2_x1_im;
    buffer6_re <= (inv_d) ? rnd_ifft3_x0_re : rnd_mdc3_x0_re;
    buffer6_im <= (inv_d) ? rnd_ifft3_x0_im : rnd_mdc3_x0_im;
    buffer7_re <= (inv_d) ? rnd_ifft3_x1_re : rnd_mdc3_x1_re;
    buffer7_im <= (inv_d) ? rnd_ifft3_x1_im : rnd_mdc3_x1_im;
end

buffer_parallel2serial #(
    .NB_DATA    (NB_DATA)
) u_buffer_parallel2serial (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .o_data_re  (o_data_re),
    .o_data_im  (o_data_im),
    .o_valid    (o_valid),
    .i_clk      (i_clk),
    .i_rstn     (i_rstn),
    .i_en       (i_en),
    .i_valid    (mdc_valid_d),
    .i_tx_ready (i_tx_ready),
    .i_data0_re (buffer0_re),
    .i_data0_im (buffer0_im),
    .i_data1_re (buffer1_re),
    .i_data1_im (buffer1_im),
    .i_data2_re (buffer2_re),
    .i_data2_im (buffer2_im),
    .i_data3_re (buffer3_re),
    .i_data3_im (buffer3_im),
    .i_data4_re (buffer4_re),
    .i_data4_im (buffer4_im),
    .i_data5_re (buffer5_re),
    .i_data5_im (buffer5_im),
    .i_data6_re (buffer6_re),
    .i_data6_im (buffer6_im),
    .i_data7_re (buffer7_re),
    .i_data7_im (buffer7_im)
);

assign o_debug_mid_re = shift_r4_data0_re;

endmodule
