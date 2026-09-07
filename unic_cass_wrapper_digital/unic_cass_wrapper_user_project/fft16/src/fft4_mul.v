//=============================================================================
// Updated: 2026-09-01
// Twiddle multiplier. Multiplies a complex sample by a Q(NB_TW,NBF_TW)
// twiddle factor and brings the product back to NB_DATA bits with rounding
// and saturation. Two pipeline stages: multiply-accumulate, then clip.
//=============================================================================

module fft4_mul #(
    parameter NB_DATA = 10,
    parameter NB_TW   = 10,
    parameter NBF_TW  =  9,
    parameter NBF_OUT =  6
) (
    `ifdef USE_POWER_PINS
    inout                       VPWR,
    inout                       VGND,
    `endif
    output signed [NB_DATA-1:0] o_data_re,
    output signed [NB_DATA-1:0] o_data_im,
    input                       i_clk,
    input                       i_en,
    input  signed [NB_DATA-1:0] i_data_re,
    input  signed [NB_DATA-1:0] i_data_im,
    input  signed [NB_TW-1:0]   i_tw_re,
    input  signed [NB_TW-1:0]   i_tw_im
);

localparam NB_PROD = NB_DATA + NB_TW + 1;

wire signed [NB_DATA+NB_TW-1:0] prod_xu;
wire signed [NB_DATA+NB_TW-1:0] prod_yv;
wire signed [NB_DATA+NB_TW-1:0] prod_xv;
wire signed [NB_DATA+NB_TW-1:0] prod_yu;

reg  signed [NB_PROD-1:0]       sum_re_d;
reg  signed [NB_PROD-1:0]       sum_im_d;

wire signed [NB_DATA-1:0]       clip_re;
wire signed [NB_DATA-1:0]       clip_im;

reg  signed [NB_DATA-1:0]       data_re_2d;
reg  signed [NB_DATA-1:0]       data_im_2d;

assign prod_xu = i_data_re * i_tw_re;
assign prod_yv = i_data_im * i_tw_im;
assign prod_xv = i_data_re * i_tw_im;
assign prod_yu = i_data_im * i_tw_re;

always @(posedge i_clk) begin
    if (i_en) begin
        sum_re_d <= prod_xu - prod_yv;
        sum_im_d <= prod_xv + prod_yu;
    end
end

clip_round #(
    .NB_INP    (NB_PROD),
    .NBF_INP   (NBF_OUT + NBF_TW),
    .NB_OUT    (NB_DATA),
    .NBF_OUT   (NBF_OUT),
    .RND_MD    (1)
) u_clip_round (
    `ifdef USE_POWER_PINS
    .VPWR      (VPWR),
    .VGND      (VGND),
    `endif
    .o_data_re (clip_re),
    .o_data_im (clip_im),
    .i_data_re (sum_re_d),
    .i_data_im (sum_im_d)
);

always @(posedge i_clk) begin
    if (i_en) begin
        data_re_2d <= clip_re;
        data_im_2d <= clip_im;
    end
end

assign o_data_re = data_re_2d;
assign o_data_im = data_im_2d;

endmodule
