module complex_multiplier #(
    parameter NB_INPUT_A   = 10,
    parameter NBF_INPUT_A  = 7,
    parameter NB_INPUT_B   = 10,
    parameter NBF_INPUT_B  = 7,
    parameter NB_OUTPUT  = 10,
    parameter NBF_OUTPUT = 7,
    parameter RND_MD     = 0
)(
    `ifdef USE_POWER_PINS
    inout               VPWR,  // Common digital supply
    inout               VGND,  // Common digital ground
    `endif
    input                          i_clk,
    ///////////////////// INPUTS  /////////////////////
    input  signed [NB_INPUT_A-1:0] i_real_A,
    input  signed [NB_INPUT_A-1:0] i_imag_A,
    input  signed [NB_INPUT_B-1:0] i_real_B,
    input  signed [NB_INPUT_B-1:0] i_imag_B,
    ///////////////////// OUTPUTS /////////////////////
    output signed [ NB_OUTPUT-1:0] o_real,
    output signed [ NB_OUTPUT-1:0] o_imag
);

///////////////////////////////////////////////////////////////////////////////
// WIRE AND REGISTER
///////////////////////////////////////////////////////////////////////////////

localparam NB_PROD      = NB_INPUT_A + NB_INPUT_B;
localparam NBF_PROD     = NBF_INPUT_A + NBF_INPUT_B;
localparam NB_PROD_SUM  = NB_PROD + 1;
localparam NBF_PROD_SUM = NBF_PROD;

wire signed [    NB_PROD-1:0] prod_xu;
wire signed [    NB_PROD-1:0] prod_yv;
wire signed [    NB_PROD-1:0] prod_xv;
wire signed [    NB_PROD-1:0] prod_yu;
wire signed [NB_PROD_SUM-1:0] sum_re;
wire signed [NB_PROD_SUM-1:0] sum_im;
wire signed [  NB_OUTPUT-1:0] w_out_re;
wire signed [  NB_OUTPUT-1:0] w_out_im;
reg  signed [  NB_OUTPUT-1:0] r_out_re;
reg  signed [  NB_OUTPUT-1:0] r_out_im;

///////////////////////////////////////////////////////////////////////////////
// CL
///////////////////////////////////////////////////////////////////////////////

assign prod_xu = i_real_A * i_real_B;
assign prod_yv = i_imag_A * i_imag_B;
assign prod_xv = i_real_A * i_imag_B;
assign prod_yu = i_imag_A * i_real_B;

assign sum_re = prod_xu - prod_yv;
assign sum_im = prod_xv + prod_yu;

clip_round #(
    .NB_INP(NB_PROD_SUM), 
    .NBF_INP(NBF_PROD_SUM), 
    .NB_OUT(NB_OUTPUT), 
    .NBF_OUT(NBF_OUTPUT),
    .RND_MD(RND_MD)
) u_clip (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .i_data_re(sum_re),
    .i_data_im(sum_im),
    .o_data_re(w_out_re),
    .o_data_im(w_out_im)
);

always @(posedge i_clk) begin
    r_out_re <= w_out_re;
    r_out_im <= w_out_im;
end

assign o_real = r_out_re;
assign o_imag = r_out_im;

endmodule