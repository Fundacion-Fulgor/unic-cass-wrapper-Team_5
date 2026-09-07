//=============================================================================
// Updated: 2026-09-01
// Second radix-2 stage of the MDC butterfly. Combines the commutated pair
// produced by stage 1 and registers the result.
//=============================================================================

module fft4_mdc_stage2 #(
    parameter NB_INPUT = 8
) (
    `ifdef USE_POWER_PINS
    inout                        VPWR,
    inout                        VGND,
    `endif
    output                       o_valid,
    output signed [NB_INPUT-0:0] o_data1_r,
    output signed [NB_INPUT-0:0] o_data1_i,
    output signed [NB_INPUT-0:0] o_data2_r,
    output signed [NB_INPUT-0:0] o_data2_i,
    input                        i_clk,
    input                        i_valid,
    input  signed [NB_INPUT-1:0] i_data1_r,
    input  signed [NB_INPUT-1:0] i_data1_i,
    input  signed [NB_INPUT-1:0] i_data2_r,
    input  signed [NB_INPUT-1:0] i_data2_i
);

wire signed [NB_INPUT-0:0] bt0_r;
wire signed [NB_INPUT-0:0] bt0_i;
wire signed [NB_INPUT-0:0] bt1_r;
wire signed [NB_INPUT-0:0] bt1_i;

reg  signed [NB_INPUT-0:0] out0_r_d;
reg  signed [NB_INPUT-0:0] out0_i_d;
reg  signed [NB_INPUT-0:0] out1_r_d;
reg  signed [NB_INPUT-0:0] out1_i_d;
reg                        valid_d;

btfly_2 #(
    .NB_INPUT  (NB_INPUT)
) u_btfly_2 (
    `ifdef USE_POWER_PINS
    .VPWR      (VPWR),
    .VGND      (VGND),
    `endif
    .o_data0_r (bt0_r),
    .o_data0_i (bt0_i),
    .o_data1_r (bt1_r),
    .o_data1_i (bt1_i),
    .i_data0_r (i_data1_r),
    .i_data0_i (i_data1_i),
    .i_data1_r (i_data2_r),
    .i_data1_i (i_data2_i)
);

always @(posedge i_clk) begin
    valid_d <= i_valid;
    if (i_valid) begin
        out0_r_d <= bt0_r;
        out0_i_d <= bt0_i;
        out1_r_d <= bt1_r;
        out1_i_d <= bt1_i;
    end
end

assign o_data1_r = out0_r_d;
assign o_data1_i = out0_i_d;
assign o_data2_r = out1_r_d;
assign o_data2_i = out1_i_d;
assign o_valid   = valid_d;

endmodule
