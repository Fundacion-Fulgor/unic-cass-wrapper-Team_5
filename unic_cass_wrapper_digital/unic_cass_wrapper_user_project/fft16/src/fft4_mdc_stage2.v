module fft4_mdc_stage2 #(
    parameter NB_INPUT   = 8
) (
    `ifdef USE_POWER_PINS
    inout                        VPWR,  // Common digital supply
    inout                        VGND,  // Common digital ground
    `endif
    input                        i_clk,
    //----------------------------------------
    input                        i_valid,
    input  signed [NB_INPUT-1:0] i_data1_r,
    input  signed [NB_INPUT-1:0] i_data1_i,
    input  signed [NB_INPUT-1:0] i_data2_r,
    input  signed [NB_INPUT-1:0] i_data2_i,
    //----------------------------------------
    output                       o_valid,
    output signed [NB_INPUT-0:0] o_data1_r,
    output signed [NB_INPUT-0:0] o_data1_i,
    output signed [NB_INPUT-0:0] o_data2_r,
    output signed [NB_INPUT-0:0] o_data2_i
);

//////////////////////////////////////////////////////////////////////////////////
// WIRE AND REGISTER
//////////////////////////////////////////////////////////////////////////////////

wire signed [NB_INPUT-0:0] w_bt0_r;
wire signed [NB_INPUT-0:0] w_bt0_i;
wire signed [NB_INPUT-0:0] w_bt1_r;
wire signed [NB_INPUT-0:0] w_bt1_i;

reg  signed [NB_INPUT-0:0] w_out0_r;
reg  signed [NB_INPUT-0:0] w_out0_i;
reg  signed [NB_INPUT-0:0] w_out1_r;
reg  signed [NB_INPUT-0:0] w_out1_i;

reg  signed [NB_INPUT-0:0] r_out0_r;
reg  signed [NB_INPUT-0:0] r_out0_i;
reg  signed [NB_INPUT-0:0] r_out1_r;
reg  signed [NB_INPUT-0:0] r_out1_i;
reg                        r_valid;

//////////////////////////////////////////////////////////////////////////////////
// MODULE
//////////////////////////////////////////////////////////////////////////////////

btfly_2 #(
    .NB_INPUT (NB_INPUT)
) u_btfly2 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .i_data0_r(i_data1_r),
    .i_data0_i(i_data1_i),
    .i_data1_r(i_data2_r),
    .i_data1_i(i_data2_i),
    .o_data0_r(w_bt0_r),
    .o_data0_i(w_bt0_i),
    .o_data1_r(w_bt1_r),
    .o_data1_i(w_bt1_i)
);

always @(posedge i_clk) begin
    r_valid <= i_valid;
    if (i_valid) begin
        r_out0_r <= w_bt0_r;
        r_out0_i <= w_bt0_i;
        r_out1_r <= w_bt1_r;
        r_out1_i <= w_bt1_i;
    end
end

assign o_data1_r = r_out0_r;
assign o_data1_i = r_out0_i;
assign o_data2_r = r_out1_r;
assign o_data2_i = r_out1_i;
assign o_valid   = r_valid;

endmodule
