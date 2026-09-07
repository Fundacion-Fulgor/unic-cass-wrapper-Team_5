//=============================================================================
// Updated: 2026-09-01
// Radix-2 butterfly. Combinational sum and difference of two complex inputs,
// with the output widened by one bit so the result cannot overflow.
//=============================================================================

module btfly_2 #(
    parameter NB_INPUT = 8
) (
    `ifdef USE_POWER_PINS
    inout                        VPWR,
    inout                        VGND,
    `endif
    output signed [NB_INPUT-0:0] o_data0_r,
    output signed [NB_INPUT-0:0] o_data0_i,
    output signed [NB_INPUT-0:0] o_data1_r,
    output signed [NB_INPUT-0:0] o_data1_i,
    input  signed [NB_INPUT-1:0] i_data0_r,
    input  signed [NB_INPUT-1:0] i_data0_i,
    input  signed [NB_INPUT-1:0] i_data1_r,
    input  signed [NB_INPUT-1:0] i_data1_i
);

assign o_data0_r = i_data0_r + i_data1_r;
assign o_data0_i = i_data0_i + i_data1_i;
assign o_data1_r = i_data0_r - i_data1_r;
assign o_data1_i = i_data0_i - i_data1_i;

endmodule
