module fft16 #(
    parameter NB_DATA   = 8
) (
    `ifdef USE_POWER_PINS
    inout                       VPWR,  // Common digital supply
    inout                       VGND,  // Common digital ground
    `endif
    input                       i_clk,
    input                       i_clk_en,
    input                       i_rst_n,
    input                       i_inverse,
    ///////////////////// INPUTS  /////////////////////
    input                       i_valid,
    input                       i_tx_ready,
    input  signed [NB_DATA-1:0] i_data_re,
    input  signed [NB_DATA-1:0] i_data_im,
    ///////////////////// OUTPUTS /////////////////////
    output                      o_valid,
    output signed [NB_DATA-1:0] o_data_re,
    output signed [NB_DATA-1:0] o_data_im,
    output signed [NB_DATA-1:0] o_debug_mid_re
);

///////////////////////////////////////////////////////////////////////////////
// WIRE AND REGISTER
///////////////////////////////////////////////////////////////////////////////

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

wire signed [NB_DATA+3:0] mdc0_shift_d0_re;
wire signed [NB_DATA+3:0] mdc0_shift_d0_im;
wire signed [NB_DATA+3:0] mdc0_shift_d1_re;
wire signed [NB_DATA+3:0] mdc0_shift_d1_im;
wire signed [NB_DATA+3:0] mdc1_shift_d0_re;
wire signed [NB_DATA+3:0] mdc1_shift_d0_im;
wire signed [NB_DATA+3:0] mdc1_shift_d1_re;
wire signed [NB_DATA+3:0] mdc1_shift_d1_im;
wire signed [NB_DATA+3:0] mdc2_shift_d0_re;
wire signed [NB_DATA+3:0] mdc2_shift_d0_im;
wire signed [NB_DATA+3:0] mdc2_shift_d1_re;
wire signed [NB_DATA+3:0] mdc2_shift_d1_im;
wire signed [NB_DATA+3:0] mdc3_shift_d0_re;
wire signed [NB_DATA+3:0] mdc3_shift_d0_im;
wire signed [NB_DATA+3:0] mdc3_shift_d1_re;
wire signed [NB_DATA+3:0] mdc3_shift_d1_im;

wire signed [NB_DATA-1:0] rnd_mdc0_d0_re;
wire signed [NB_DATA-1:0] rnd_mdc0_d0_im;
wire signed [NB_DATA-1:0] rnd_mdc0_d1_re;
wire signed [NB_DATA-1:0] rnd_mdc0_d1_im;
wire signed [NB_DATA-1:0] rnd_mdc1_d0_re;
wire signed [NB_DATA-1:0] rnd_mdc1_d0_im;
wire signed [NB_DATA-1:0] rnd_mdc1_d1_re;
wire signed [NB_DATA-1:0] rnd_mdc1_d1_im;
wire signed [NB_DATA-1:0] rnd_mdc2_d0_re;
wire signed [NB_DATA-1:0] rnd_mdc2_d0_im;
wire signed [NB_DATA-1:0] rnd_mdc2_d1_re;
wire signed [NB_DATA-1:0] rnd_mdc2_d1_im;
wire signed [NB_DATA-1:0] rnd_mdc3_d0_re;
wire signed [NB_DATA-1:0] rnd_mdc3_d0_im;
wire signed [NB_DATA-1:0] rnd_mdc3_d1_re;
wire signed [NB_DATA-1:0] rnd_mdc3_d1_im;

wire signed [NB_DATA-1:0] rnd_ifft0_d0_re;
wire signed [NB_DATA-1:0] rnd_ifft0_d0_im;
wire signed [NB_DATA-1:0] rnd_ifft0_d1_re;
wire signed [NB_DATA-1:0] rnd_ifft0_d1_im;
wire signed [NB_DATA-1:0] rnd_ifft1_d0_re;
wire signed [NB_DATA-1:0] rnd_ifft1_d0_im;
wire signed [NB_DATA-1:0] rnd_ifft1_d1_re;
wire signed [NB_DATA-1:0] rnd_ifft1_d1_im;
wire signed [NB_DATA-1:0] rnd_ifft2_d0_re;
wire signed [NB_DATA-1:0] rnd_ifft2_d0_im;
wire signed [NB_DATA-1:0] rnd_ifft2_d1_re;
wire signed [NB_DATA-1:0] rnd_ifft2_d1_im;
wire signed [NB_DATA-1:0] rnd_ifft3_d0_re;
wire signed [NB_DATA-1:0] rnd_ifft3_d0_im;
wire signed [NB_DATA-1:0] rnd_ifft3_d1_re;
wire signed [NB_DATA-1:0] rnd_ifft3_d1_im;


wire signed [NB_DATA-1:0] buffer0_re;
wire signed [NB_DATA-1:0] buffer0_im;
wire signed [NB_DATA-1:0] buffer1_re;
wire signed [NB_DATA-1:0] buffer1_im;
wire signed [NB_DATA-1:0] buffer2_re;
wire signed [NB_DATA-1:0] buffer2_im;
wire signed [NB_DATA-1:0] buffer3_re;
wire signed [NB_DATA-1:0] buffer3_im;
wire signed [NB_DATA-1:0] buffer4_re;
wire signed [NB_DATA-1:0] buffer4_im;
wire signed [NB_DATA-1:0] buffer5_re;
wire signed [NB_DATA-1:0] buffer5_im;
wire signed [NB_DATA-1:0] buffer6_re;
wire signed [NB_DATA-1:0] buffer6_im;
wire signed [NB_DATA-1:0] buffer7_re;
wire signed [NB_DATA-1:0] buffer7_im;


////////////////////////////////////////////////////////////////////////////////////////////

fft16_shift_r4 #( .NB_DATA(NB_DATA)) u_fft16_shift_r4 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .i_clk      (i_clk),
    .i_clk_en   (i_clk_en),
    .i_rst_n    (i_rst_n),
    //---------------------------------------------------------
    .i_valid    (i_valid),
    .i_data_re  (i_data_re),
    .i_data_im  (i_data_im),
    //---------------------------------------------------------
    .o_data0_re (shift_r4_data0_re),
    .o_data0_im (shift_r4_data0_im),
    .o_data1_re (shift_r4_data1_re),
    .o_data1_im (shift_r4_data1_im),
    .o_data2_re (shift_r4_data2_re),
    .o_data2_im (shift_r4_data2_im),
    .o_data3_re (shift_r4_data3_re),
    .o_data3_im (shift_r4_data3_im),
    .o_valid    (shift_r4_valid)
);

////////////////////////////////////////////////////////////////////////////////////////////

fft4_radix4 #( .NB_INPUT(NB_DATA)) u_fft4_radix4 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .i_clk      (i_clk),
    .i_rst_n    (i_rst_n),
    .i_inverse  (i_inverse),
    .i_enable   (i_clk_en),
    .i_valid    (shift_r4_valid),
    //---------------------------------------------------------
    .i_data0_re (shift_r4_data0_re),
    .i_data0_im (shift_r4_data0_im),
    .i_data1_re (shift_r4_data1_re),
    .i_data1_im (shift_r4_data1_im),
    .i_data2_re (shift_r4_data2_re),
    .i_data2_im (shift_r4_data2_im),
    .i_data3_re (shift_r4_data3_re),
    .i_data3_im (shift_r4_data3_im),
    //---------------------------------------------------------
    .o_data0_re (fft4_data0_re),
    .o_data0_im (fft4_data0_im),
    .o_data1_re (fft4_data1_re),
    .o_data1_im (fft4_data1_im),
    .o_data2_re (fft4_data2_re),
    .o_data2_im (fft4_data2_im),
    .o_data3_re (fft4_data3_re),
    .o_data3_im (fft4_data3_im),
    .o_valid    (fft4_valid)
);


////////////////////////////////////////////////////////////////////////////////////////////

fft16_shift_r2 #( .NB_DATA(NB_DATA+2)) u_shift_r2_fft0 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .i_clk      (i_clk),
    .i_clk_en   (i_clk_en),
    .i_rst_n    (i_rst_n),
    //---------------------------------------------------------
    .i_valid    (fft4_valid),
    .i_data_re  (fft4_data0_re),
    .i_data_im  (fft4_data0_im),
    //---------------------------------------------------------
    .o_data0_re (shift_r2_ff0_data0_re),
    .o_data0_im (shift_r2_ff0_data0_im),
    .o_data1_re (shift_r2_ff0_data1_re),
    .o_data1_im (shift_r2_ff0_data1_im),
    .o_valid    (shift_r2_ff0_valid)
);

fft16_shift_r2 #( .NB_DATA(NB_DATA+2)) u_shift_r2_fft1 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .i_clk      (i_clk),
    .i_clk_en   (i_clk_en),
    .i_rst_n    (i_rst_n),
    //---------------------------------------------------------
    .i_valid    (fft4_valid),
    .i_data_re  (fft4_data1_re),
    .i_data_im  (fft4_data1_im),
    //---------------------------------------------------------
    .o_data0_re (shift_r2_ff1_data0_re),
    .o_data0_im (shift_r2_ff1_data0_im),
    .o_data1_re (shift_r2_ff1_data1_re),
    .o_data1_im (shift_r2_ff1_data1_im),
    .o_valid    (shift_r2_ff1_valid)
);

fft16_shift_r2 #( .NB_DATA(NB_DATA+2)) u_shift_r2_fft2 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .i_clk      (i_clk),
    .i_clk_en   (i_clk_en),
    .i_rst_n    (i_rst_n),
    //---------------------------------------------------------
    .i_valid    (fft4_valid),
    .i_data_re  (fft4_data2_re),
    .i_data_im  (fft4_data2_im),
    //---------------------------------------------------------
    .o_data0_re (shift_r2_ff2_data0_re),
    .o_data0_im (shift_r2_ff2_data0_im),
    .o_data1_re (shift_r2_ff2_data1_re),
    .o_data1_im (shift_r2_ff2_data1_im),
    .o_valid    (shift_r2_ff2_valid)
);

fft16_shift_r2 #( .NB_DATA(NB_DATA+2)) u_shift_r2_fft3 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .i_clk      (i_clk),
    .i_clk_en   (i_clk_en),
    .i_rst_n    (i_rst_n),
    //---------------------------------------------------------
    .i_valid    (fft4_valid),
    .i_data_re  (fft4_data3_re),
    .i_data_im  (fft4_data3_im),
    //---------------------------------------------------------
    .o_data0_re (shift_r2_ff3_data0_re),
    .o_data0_im (shift_r2_ff3_data0_im),
    .o_data1_re (shift_r2_ff3_data1_re),
    .o_data1_im (shift_r2_ff3_data1_im),
    .o_valid    (shift_r2_ff3_valid)
);

////////////////////////////////////////////////////////////////////////////////////////////

fft4_mdc #( .NB_INPUT(NB_DATA+2)) u_fft4_mdc0 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .i_clk      (i_clk),
    .i_rst_n    (i_rst_n),
    .i_inverse  (i_inverse),
    //---------------------------------------------------------
    .i_valid    (shift_r2_ff0_valid),
    .i_data1_r  (shift_r2_ff0_data0_re),
    .i_data1_i  (shift_r2_ff0_data0_im),
    .i_data2_r  (shift_r2_ff0_data1_re),
    .i_data2_i  (shift_r2_ff0_data1_im),
    //---------------------------------------------------------
    .o_valid    (mdc_ff0_valid),
    .o_data1_r  (mdc_ff0_data0_re),
    .o_data1_i  (mdc_ff0_data0_im),
    .o_data2_r  (mdc_ff0_data1_re),
    .o_data2_i  (mdc_ff0_data1_im)
);

fft4_mdc #( .NB_INPUT(NB_DATA+2)) u_fft4_mdc1 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .i_clk      (i_clk),
    .i_rst_n    (i_rst_n),
    .i_inverse  (i_inverse),
    //---------------------------------------------------------
    .i_valid    (shift_r2_ff1_valid),
    .i_data1_r  (shift_r2_ff1_data0_re),
    .i_data1_i  (shift_r2_ff1_data0_im),
    .i_data2_r  (shift_r2_ff1_data1_re),
    .i_data2_i  (shift_r2_ff1_data1_im),
    //---------------------------------------------------------
    .o_valid    (mdc_ff1_valid),
    .o_data1_r  (mdc_ff1_data0_re),
    .o_data1_i  (mdc_ff1_data0_im),
    .o_data2_r  (mdc_ff1_data1_re),
    .o_data2_i  (mdc_ff1_data1_im)
);

fft4_mdc #( .NB_INPUT(NB_DATA+2)) u_fft4_mdc2 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .i_clk      (i_clk),
    .i_rst_n    (i_rst_n),
    .i_inverse  (i_inverse),
    //---------------------------------------------------------
    .i_valid    (shift_r2_ff2_valid),
    .i_data1_r  (shift_r2_ff2_data0_re),
    .i_data1_i  (shift_r2_ff2_data0_im),
    .i_data2_r  (shift_r2_ff2_data1_re),
    .i_data2_i  (shift_r2_ff2_data1_im),
    //---------------------------------------------------------
    .o_valid    (mdc_ff2_valid),
    .o_data1_r  (mdc_ff2_data0_re),
    .o_data1_i  (mdc_ff2_data0_im),
    .o_data2_r  (mdc_ff2_data1_re),
    .o_data2_i  (mdc_ff2_data1_im)
);

fft4_mdc #( .NB_INPUT(NB_DATA+2)) u_fft4_mdc3 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .i_clk      (i_clk),
    .i_rst_n    (i_rst_n),
    .i_inverse  (i_inverse),
    //---------------------------------------------------------
    .i_valid    (shift_r2_ff3_valid),
    .i_data1_r  (shift_r2_ff3_data0_re),
    .i_data1_i  (shift_r2_ff3_data0_im),
    .i_data2_r  (shift_r2_ff3_data1_re),
    .i_data2_i  (shift_r2_ff3_data1_im),
    //---------------------------------------------------------
    .o_valid    (mdc_ff3_valid),
    .o_data1_r  (mdc_ff3_data0_re),
    .o_data1_i  (mdc_ff3_data0_im),
    .o_data2_r  (mdc_ff3_data1_re),
    .o_data2_i  (mdc_ff3_data1_im)
);

assign mdc_ffx_valid = mdc_ff0_valid & mdc_ff1_valid & mdc_ff2_valid & mdc_ff3_valid;

////////////////////////////////////////////////////////////////////////////////////////////

assign mdc0_shift_d0_re = mdc_ff0_data0_re;
assign mdc0_shift_d0_im = mdc_ff0_data0_im;
assign mdc0_shift_d1_re = mdc_ff0_data1_re;
assign mdc0_shift_d1_im = mdc_ff0_data1_im;
assign mdc1_shift_d0_re = mdc_ff1_data0_re;
assign mdc1_shift_d0_im = mdc_ff1_data0_im;
assign mdc1_shift_d1_re = mdc_ff1_data1_re;
assign mdc1_shift_d1_im = mdc_ff1_data1_im;
assign mdc2_shift_d0_re = mdc_ff2_data0_re;
assign mdc2_shift_d0_im = mdc_ff2_data0_im;
assign mdc2_shift_d1_re = mdc_ff2_data1_re;
assign mdc2_shift_d1_im = mdc_ff2_data1_im;
assign mdc3_shift_d0_re = mdc_ff3_data0_re;
assign mdc3_shift_d0_im = mdc_ff3_data0_im;
assign mdc3_shift_d1_re = mdc_ff3_data1_re;
assign mdc3_shift_d1_im = mdc_ff3_data1_im;

////////////////////////////////////////////////////////////////////////////////////////////

clip_round#( .NB_INP(NB_DATA+4), .NBF_INP(NB_DATA-2), .NB_OUT(NB_DATA), .NBF_OUT(NB_DATA-5), .RND_MD(0)
) u_mdc0_clip_round_d0 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .i_data_re(mdc0_shift_d0_re),
    .i_data_im(mdc0_shift_d0_im),
    .o_data_re(rnd_mdc0_d0_re),
    .o_data_im(rnd_mdc0_d0_im)
);

clip_round#( .NB_INP(NB_DATA+4), .NBF_INP(NB_DATA-2), .NB_OUT(NB_DATA), .NBF_OUT(NB_DATA-5), .RND_MD(0)
) u_mdc0_clip_round_d1 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .i_data_re(mdc0_shift_d1_re),
    .i_data_im(mdc0_shift_d1_im),
    .o_data_re(rnd_mdc0_d1_re),
    .o_data_im(rnd_mdc0_d1_im)
);

clip_round#( .NB_INP(NB_DATA+4), .NBF_INP(NB_DATA-1), .NB_OUT(NB_DATA), .NBF_OUT(NB_DATA-2), .RND_MD(0)
) u_ifft0_clip_round_d0 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .i_data_re(mdc0_shift_d0_re),
    .i_data_im(mdc0_shift_d0_im),
    .o_data_re(rnd_ifft0_d0_re),
    .o_data_im(rnd_ifft0_d0_im)
);

clip_round#( .NB_INP(NB_DATA+4), .NBF_INP(NB_DATA-1), .NB_OUT(NB_DATA), .NBF_OUT(NB_DATA-2), .RND_MD(0)
) u_ifft0_clip_round_d1 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .i_data_re(mdc0_shift_d1_re),
    .i_data_im(mdc0_shift_d1_im),
    .o_data_re(rnd_ifft0_d1_re),
    .o_data_im(rnd_ifft0_d1_im)
);


//---------------------------------------------------------

clip_round#( .NB_INP(NB_DATA+4), .NBF_INP(NB_DATA-2), .NB_OUT(NB_DATA), .NBF_OUT(NB_DATA-5), .RND_MD(0)
) u_mdc1_clip_round_d0 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .i_data_re(mdc1_shift_d0_re),
    .i_data_im(mdc1_shift_d0_im),
    .o_data_re(rnd_mdc1_d0_re),
    .o_data_im(rnd_mdc1_d0_im)
);

clip_round#( .NB_INP(NB_DATA+4), .NBF_INP(NB_DATA-2), .NB_OUT(NB_DATA), .NBF_OUT(NB_DATA-5), .RND_MD(0)
) u_mdc1_clip_round_d1 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .i_data_re(mdc1_shift_d1_re),
    .i_data_im(mdc1_shift_d1_im),
    .o_data_re(rnd_mdc1_d1_re),
    .o_data_im(rnd_mdc1_d1_im)
);

clip_round#( .NB_INP(NB_DATA+4), .NBF_INP(NB_DATA-1), .NB_OUT(NB_DATA), .NBF_OUT(NB_DATA-2), .RND_MD(0)
) u_ifft1_clip_round_d0 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .i_data_re(mdc1_shift_d0_re),
    .i_data_im(mdc1_shift_d0_im),
    .o_data_re(rnd_ifft1_d0_re),
    .o_data_im(rnd_ifft1_d0_im)
);

clip_round#( .NB_INP(NB_DATA+4), .NBF_INP(NB_DATA-1), .NB_OUT(NB_DATA), .NBF_OUT(NB_DATA-2), .RND_MD(0)
) u_ifft1_clip_round_d1 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .i_data_re(mdc1_shift_d1_re),
    .i_data_im(mdc1_shift_d1_im),
    .o_data_re(rnd_ifft1_d1_re),
    .o_data_im(rnd_ifft1_d1_im)
);

//---------------------------------------------------------

clip_round#( .NB_INP(NB_DATA+4), .NBF_INP(NB_DATA-2), .NB_OUT(NB_DATA), .NBF_OUT(NB_DATA-5), .RND_MD(0)
) u_mdc2_clip_round_d0 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .i_data_re(mdc2_shift_d0_re),
    .i_data_im(mdc2_shift_d0_im),
    .o_data_re(rnd_mdc2_d0_re),
    .o_data_im(rnd_mdc2_d0_im)
);

clip_round#( .NB_INP(NB_DATA+4), .NBF_INP(NB_DATA-2), .NB_OUT(NB_DATA), .NBF_OUT(NB_DATA-5), .RND_MD(0)
) u_mdc2_clip_round_d1 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .i_data_re(mdc2_shift_d1_re),
    .i_data_im(mdc2_shift_d1_im),
    .o_data_re(rnd_mdc2_d1_re),
    .o_data_im(rnd_mdc2_d1_im)
);

clip_round#( .NB_INP(NB_DATA+4), .NBF_INP(NB_DATA-1), .NB_OUT(NB_DATA), .NBF_OUT(NB_DATA-2), .RND_MD(0)
) u_ifft2_clip_round_d0 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .i_data_re(mdc2_shift_d0_re),
    .i_data_im(mdc2_shift_d0_im),
    .o_data_re(rnd_ifft2_d0_re),
    .o_data_im(rnd_ifft2_d0_im)
);

clip_round#( .NB_INP(NB_DATA+4), .NBF_INP(NB_DATA-1), .NB_OUT(NB_DATA), .NBF_OUT(NB_DATA-2), .RND_MD(0)
) u_ifft2_clip_round_d1 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .i_data_re(mdc2_shift_d1_re),
    .i_data_im(mdc2_shift_d1_im),
    .o_data_re(rnd_ifft2_d1_re),
    .o_data_im(rnd_ifft2_d1_im)
);

//---------------------------------------------------------

clip_round#( .NB_INP(NB_DATA+4), .NBF_INP(NB_DATA-2), .NB_OUT(NB_DATA), .NBF_OUT(NB_DATA-5), .RND_MD(0)
) u_mdc3_clip_round_d0 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .i_data_re(mdc3_shift_d0_re),
    .i_data_im(mdc3_shift_d0_im),
    .o_data_re(rnd_mdc3_d0_re),
    .o_data_im(rnd_mdc3_d0_im)
);

clip_round#( .NB_INP(NB_DATA+4), .NBF_INP(NB_DATA-2), .NB_OUT(NB_DATA), .NBF_OUT(NB_DATA-5), .RND_MD(0)
) u_mdc3_clip_round_d1 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .i_data_re(mdc3_shift_d1_re),
    .i_data_im(mdc3_shift_d1_im),
    .o_data_re(rnd_mdc3_d1_re),
    .o_data_im(rnd_mdc3_d1_im)
);

clip_round#( .NB_INP(NB_DATA+4), .NBF_INP(NB_DATA-1), .NB_OUT(NB_DATA), .NBF_OUT(NB_DATA-2), .RND_MD(0)
) u_ifft3_clip_round_d0 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .i_data_re(mdc3_shift_d0_re),
    .i_data_im(mdc3_shift_d0_im),
    .o_data_re(rnd_ifft3_d0_re),
    .o_data_im(rnd_ifft3_d0_im)
);

clip_round#( .NB_INP(NB_DATA+4), .NBF_INP(NB_DATA-1), .NB_OUT(NB_DATA), .NBF_OUT(NB_DATA-2), .RND_MD(0)
) u_ifft3_clip_round_d1 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .i_data_re(mdc3_shift_d1_re),
    .i_data_im(mdc3_shift_d1_im),
    .o_data_re(rnd_ifft3_d1_re),
    .o_data_im(rnd_ifft3_d1_im)
);

////////////////////////////////////////////////////////////////////////////////////////////

assign buffer0_re = (i_inverse)? rnd_ifft0_d0_re : rnd_mdc0_d0_re;
assign buffer0_im = (i_inverse)? rnd_ifft0_d0_im : rnd_mdc0_d0_im;
assign buffer1_re = (i_inverse)? rnd_ifft0_d1_re : rnd_mdc0_d1_re;
assign buffer1_im = (i_inverse)? rnd_ifft0_d1_im : rnd_mdc0_d1_im;
assign buffer2_re = (i_inverse)? rnd_ifft1_d0_re : rnd_mdc1_d0_re;
assign buffer2_im = (i_inverse)? rnd_ifft1_d0_im : rnd_mdc1_d0_im;
assign buffer3_re = (i_inverse)? rnd_ifft1_d1_re : rnd_mdc1_d1_re;
assign buffer3_im = (i_inverse)? rnd_ifft1_d1_im : rnd_mdc1_d1_im;
assign buffer4_re = (i_inverse)? rnd_ifft2_d0_re : rnd_mdc2_d0_re;
assign buffer4_im = (i_inverse)? rnd_ifft2_d0_im : rnd_mdc2_d0_im;
assign buffer5_re = (i_inverse)? rnd_ifft2_d1_re : rnd_mdc2_d1_re;
assign buffer5_im = (i_inverse)? rnd_ifft2_d1_im : rnd_mdc2_d1_im;
assign buffer6_re = (i_inverse)? rnd_ifft3_d0_re : rnd_mdc3_d0_re;
assign buffer6_im = (i_inverse)? rnd_ifft3_d0_im : rnd_mdc3_d0_im;
assign buffer7_re = (i_inverse)? rnd_ifft3_d1_re : rnd_mdc3_d1_re;
assign buffer7_im = (i_inverse)? rnd_ifft3_d1_im : rnd_mdc3_d1_im;

buffer_parallel2serial #( .NB_DATA(NB_DATA)) u_buffer_parallel2serial (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .i_clk      (i_clk),
    .i_rst_n    (i_rst_n),
    .i_clk_en   (i_clk_en),
    .i_valid    (mdc_ffx_valid),
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
    .i_data7_im (buffer7_im),
    .o_data_re  (o_data_re),
    .o_data_im  (o_data_im),
    .o_valid    (o_valid)
);

assign o_debug_mid_re = shift_r4_data0_re;

endmodule