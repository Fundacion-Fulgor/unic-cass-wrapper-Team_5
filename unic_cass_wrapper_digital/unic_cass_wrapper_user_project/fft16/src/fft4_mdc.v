module fft4_mdc #(
    parameter NB_INPUT   = 8
) (
    `ifdef USE_POWER_PINS
    inout                        VPWR,  // Common digital supply
    inout                        VGND,  // Common digital ground
    `endif
    input                        i_clk,
    input                        i_rst_n,
    input                        i_inverse,
    ///////////////////// INPUTS  /////////////////////
    input                        i_valid,
    input  signed [NB_INPUT-1:0] i_data1_r,
    input  signed [NB_INPUT-1:0] i_data1_i,
    input  signed [NB_INPUT-1:0] i_data2_r,
    input  signed [NB_INPUT-1:0] i_data2_i,
    ///////////////////// OUTPUTS /////////////////////
    output                       o_valid,
    output signed [NB_INPUT+1:0] o_data1_r,
    output signed [NB_INPUT+1:0] o_data1_i,
    output signed [NB_INPUT+1:0] o_data2_r,
    output signed [NB_INPUT+1:0] o_data2_i
);


///////////////////////////////////////////////////////////////////////////////
// WIRE AND REGISTER
///////////////////////////////////////////////////////////////////////////////

wire [NB_INPUT-0:0] w_out_stg1_1r;
wire [NB_INPUT-0:0] w_out_stg1_1i;
wire [NB_INPUT-0:0] w_out_stg1_2r;
wire [NB_INPUT-0:0] w_out_stg1_2i;
wire                w_out_stg1_valid;


///////////////////////////////////////////////////////////////////////////////
// MODULES
///////////////////////////////////////////////////////////////////////////////

fft4_mdc_stage1 #(
    .NB_INPUT  (NB_INPUT)
) u_fft4_mdc_stage1 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .i_clk      (i_clk),
    .i_rst_n    (i_rst_n),
    .i_inverse  (i_inverse),
    //----------------------------------------
    .i_valid    (i_valid),
    .i_data1_r  (i_data1_r),
    .i_data1_i  (i_data1_i),
    .i_data2_r  (i_data2_r),
    .i_data2_i  (i_data2_i),
    //----------------------------------------
    .o_valid    (w_out_stg1_valid),
    .o_data1_r  (w_out_stg1_1r),
    .o_data1_i  (w_out_stg1_1i),
    .o_data2_r  (w_out_stg1_2r),
    .o_data2_i  (w_out_stg1_2i)
);

fft4_mdc_stage2 #(
    .NB_INPUT (NB_INPUT+1)
) u_fft4_mdc_stage2 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .i_clk      (i_clk),
    //----------------------------------------
    .i_valid    (w_out_stg1_valid),
    .i_data1_r  (w_out_stg1_1r),
    .i_data1_i  (w_out_stg1_1i),
    .i_data2_r  (w_out_stg1_2r),
    .i_data2_i  (w_out_stg1_2i),
    //----------------------------------------
    .o_valid    (o_valid),
    .o_data1_r  (o_data1_r),
    .o_data1_i  (o_data1_i),
    .o_data2_r  (o_data2_r),
    .o_data2_i  (o_data2_i)
);


endmodule