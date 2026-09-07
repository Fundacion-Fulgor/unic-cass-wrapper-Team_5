//=============================================================================
// Updated: 2026-09-01
// First radix-2 stage of the MDC butterfly. Applies the -j (or +j for the
// inverse transform) rotation on every second input pair and hands the result
// to the delay commutator.
//=============================================================================

module fft4_mdc_stage1 #(
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
    input                        i_rstn,
    input                        i_inverse,
    input                        i_valid,
    input  signed [NB_INPUT-1:0] i_data1_r,
    input  signed [NB_INPUT-1:0] i_data1_i,
    input  signed [NB_INPUT-1:0] i_data2_r,
    input  signed [NB_INPUT-1:0] i_data2_i
);

reg                        count;
reg                        valid_d;
reg  signed [NB_INPUT-1:0] data0_r_d;
reg  signed [NB_INPUT-1:0] data0_i_d;
reg  signed [NB_INPUT-1:0] data1_r_d;
reg  signed [NB_INPUT-1:0] data1_i_d;

wire signed [NB_INPUT-0:0] bt0_r;
wire signed [NB_INPUT-0:0] bt0_i;
wire signed [NB_INPUT-0:0] bt1_r;
wire signed [NB_INPUT-0:0] bt1_i;

wire signed [NB_INPUT-0:0] rot_r;
wire signed [NB_INPUT-0:0] rot_i;
wire signed [NB_INPUT-0:0] ds1_r;
wire signed [NB_INPUT-0:0] ds1_i;

always @(posedge i_clk) begin
    if (!i_rstn) begin
        count <= 1'b0;
    end
    else if (valid_d) begin
        count <= ~count;
    end
end

always @(posedge i_clk) begin
    valid_d <= i_valid;
    if (i_valid) begin
        data0_r_d <= i_data1_r;
        data0_i_d <= i_data1_i;
        data1_r_d <= i_data2_r;
        data1_i_d <= i_data2_i;
    end
end

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
    .i_data0_r (data0_r_d),
    .i_data0_i (data0_i_d),
    .i_data1_r (data1_r_d),
    .i_data1_i (data1_i_d)
);

assign rot_r = (i_inverse) ? -bt1_i : bt1_i;
assign rot_i = (i_inverse) ?  bt1_r : -bt1_r;
assign ds1_r = (count == 1'b1) ? rot_r : bt1_r;
assign ds1_i = (count == 1'b1) ? rot_i : bt1_i;

ds_switch #(
    .NB        (NB_INPUT+1)
) u_ds_switch (
    `ifdef USE_POWER_PINS
    .VPWR      (VPWR),
    .VGND      (VGND),
    `endif
    .o_valid   (o_valid),
    .o_data_0r (o_data1_r),
    .o_data_0i (o_data1_i),
    .o_data_1r (o_data2_r),
    .o_data_1i (o_data2_i),
    .i_clk     (i_clk),
    .i_rstn    (i_rstn),
    .i_valid   (valid_d),
    .i_data_0r (bt0_r),
    .i_data_0i (bt0_i),
    .i_data_1r (ds1_r),
    .i_data_1i (ds1_i)
);

endmodule
