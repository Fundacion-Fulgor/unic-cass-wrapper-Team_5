module btfly_2 #(
    parameter NB_INPUT  = 8,
    parameter NB_OUTPUT = 9
) (
    `ifdef USE_POWER_PINS
    inout                        VPWR,  // Common digital supply
    inout                        VGND,  // Common digital ground
    `endif
    input  signed [NB_INPUT-1:0] i_data0_r,
    input  signed [NB_INPUT-1:0] i_data0_i,
    input  signed [NB_INPUT-1:0] i_data1_r,
    input  signed [NB_INPUT-1:0] i_data1_i,
    //--------------------------------------
    output signed [NB_INPUT-0:0] o_data0_r,
    output signed [NB_INPUT-0:0] o_data0_i,
    output signed [NB_INPUT-0:0] o_data1_r,
    output signed [NB_INPUT-0:0] o_data1_i
);

/////////////////////////////////////////////////////////////////
// CL
/////////////////////////////////////////////////////////////////

assign o_data0_r   = i_data0_r + i_data1_r;
assign o_data0_i   = i_data0_i + i_data1_i;

assign o_data1_r   = i_data0_r - i_data1_r;
assign o_data1_i   = i_data0_i - i_data1_i;


endmodule
