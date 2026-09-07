//=============================================================================
// Updated: 2026-09-01
// Radix-2 multipath delay commutator pair. Chains the two MDC butterfly
// stages that together implement one radix-4 stage of the FFT16.
//=============================================================================

module fft4_mdc #(
    parameter NB_INPUT = 8
) (
    `ifdef USE_POWER_PINS
    inout                        VPWR,
    inout                        VGND,
    `endif
    output                       o_valid,
    output signed [NB_INPUT+1:0] o_data1_r,
    output signed [NB_INPUT+1:0] o_data1_i,
    output signed [NB_INPUT+1:0] o_data2_r,
    output signed [NB_INPUT+1:0] o_data2_i,
    input                        i_clk,
    input                        i_rstn,
    input                        i_inverse,
    input                        i_valid,
    input  signed [NB_INPUT-1:0] i_data1_r,
    input  signed [NB_INPUT-1:0] i_data1_i,
    input  signed [NB_INPUT-1:0] i_data2_r,
    input  signed [NB_INPUT-1:0] i_data2_i
);

wire [NB_INPUT-0:0] stg1_1r;
wire [NB_INPUT-0:0] stg1_1i;
wire [NB_INPUT-0:0] stg1_2r;
wire [NB_INPUT-0:0] stg1_2i;
wire                stg1_valid;

fft4_mdc_stage1 #(
    .NB_INPUT   (NB_INPUT)
) u_fft4_mdc_stage1 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .o_valid    (stg1_valid),
    .o_data1_r  (stg1_1r),
    .o_data1_i  (stg1_1i),
    .o_data2_r  (stg1_2r),
    .o_data2_i  (stg1_2i),
    .i_clk      (i_clk),
    .i_rstn     (i_rstn),
    .i_inverse  (i_inverse),
    .i_valid    (i_valid),
    .i_data1_r  (i_data1_r),
    .i_data1_i  (i_data1_i),
    .i_data2_r  (i_data2_r),
    .i_data2_i  (i_data2_i)
);

fft4_mdc_stage2 #(
    .NB_INPUT   (NB_INPUT+1)
) u_fft4_mdc_stage2 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .o_valid    (o_valid),
    .o_data1_r  (o_data1_r),
    .o_data1_i  (o_data1_i),
    .o_data2_r  (o_data2_r),
    .o_data2_i  (o_data2_i),
    .i_clk      (i_clk),
    .i_valid    (stg1_valid),
    .i_data1_r  (stg1_1r),
    .i_data1_i  (stg1_1i),
    .i_data2_r  (stg1_2r),
    .i_data2_i  (stg1_2i)
);

endmodule
