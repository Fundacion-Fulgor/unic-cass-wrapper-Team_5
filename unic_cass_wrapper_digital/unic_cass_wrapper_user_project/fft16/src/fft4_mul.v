module fft4_mul (
    `ifdef USE_POWER_PINS
    inout                  VPWR,  // Common digital supply
    inout                  VGND,  // Common digital ground
    `endif
    input                  i_clk,
    input                  i_inverse,
    ///////////////////// INPUTS  /////////////////////
    input  signed [10-1:0] i_data_re,
    input  signed [10-1:0] i_data_im,
    input  signed [10-1:0] i_tw_re,
    input  signed [10-1:0] i_tw_im,
    ///////////////////// OUTPUTS /////////////////////
    output signed [10-1:0] o_data_re,
    output signed [10-1:0] o_data_im
);

///////////////////////////////////////////////////////////////////////////////
// WIRE AND REGISTER
///////////////////////////////////////////////////////////////////////////////

wire signed [20-1:0] prod_xu;
wire signed [20-1:0] prod_yv;
wire signed [20-1:0] prod_xv;
wire signed [20-1:0] prod_yu;
wire signed [21-1:0] sum_re;
wire signed [21-1:0] sum_im;

wire signed [10-1:0] w_fft_re;
wire signed [10-1:0] w_fft_im;
wire signed [10-1:0] w_ifft_re;
wire signed [10-1:0] w_ifft_im;

reg  signed [10-1:0] r_out_re;
reg  signed [10-1:0] r_out_im;

///////////////////////////////////////////////////////////////////////////////
// CL
///////////////////////////////////////////////////////////////////////////////

assign prod_xu = i_data_re * i_tw_re;
assign prod_yv = i_data_im * i_tw_im;
assign prod_xv = i_data_re * i_tw_im;
assign prod_yu = i_data_im * i_tw_re;

assign sum_re = prod_xu - prod_yv;
assign sum_im = prod_xv + prod_yu;

clip_round #(
    .NB_INP     (21), 
    .NBF_INP    (6+9), 
    .NB_OUT     (10), 
    .NBF_OUT    (6),
    .RND_MD     (1)
) u_clip_fft (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .i_data_re  (sum_re),
    .i_data_im  (sum_im),
    .o_data_re  (w_fft_re),
    .o_data_im  (w_fft_im)
);

clip_round #(
    .NB_INP     (21), 
    .NBF_INP    (3+9), 
    .NB_OUT     (10), 
    .NBF_OUT    (3),
    .RND_MD     (1)
) u_clip_ifft (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .i_data_re  (sum_re),
    .i_data_im  (sum_im),
    .o_data_re  (w_ifft_re),
    .o_data_im  (w_ifft_im)
);

always @(posedge i_clk) begin
    r_out_re <= (i_inverse)? w_ifft_re : w_fft_re;
    r_out_im <= (i_inverse)? w_ifft_im : w_fft_im;
end

assign o_data_re = r_out_re;
assign o_data_im = r_out_im;

endmodule