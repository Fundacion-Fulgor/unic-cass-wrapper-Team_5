module fft4_mdc_stage1 #(
    parameter NB_INPUT   = 8
) (
    `ifdef USE_POWER_PINS
    inout                        VPWR,  // Common digital supply
    inout                        VGND,  // Common digital ground
    `endif
    input                        i_clk,
    input                        i_rst_n,
    input                        i_inverse,
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

reg                        r_count;
reg                        last_valid;
//--- -------------------------------------------
reg signed  [NB_INPUT-1:0] r_data0_r;
reg signed  [NB_INPUT-1:0] r_data0_i;
reg signed  [NB_INPUT-1:0] r_data1_r;
reg signed  [NB_INPUT-1:0] r_data1_i;
reg                        r_data_valid;
//--- -------------------------------------------
wire signed [NB_INPUT-0:0] w_bt0_r;
wire signed [NB_INPUT-0:0] w_bt0_i;
wire signed [NB_INPUT-0:0] w_bt1_r;
wire signed [NB_INPUT-0:0] w_bt1_i;
//----------------------------------------------
wire signed [NB_INPUT-0:0] w_ds0_r;
wire signed [NB_INPUT-0:0] w_ds0_i;
wire signed [NB_INPUT-0:0] w_pre_ds1_r;
wire signed [NB_INPUT-0:0] w_pre_ds1_i;
wire signed [NB_INPUT-0:0] w_ds1_r;
wire signed [NB_INPUT-0:0] w_ds1_i;

//////////////////////////////////////////////////////////////////////////////////
// FSM
//////////////////////////////////////////////////////////////////////////////////

always @(posedge i_clk or negedge i_rst_n) begin
  if (!i_rst_n) begin
    r_count <= 1'b0;
  end else begin
    if (r_data_valid) begin
      r_count <= ~r_count;
    end else begin
      r_count <= r_count;
    end
  end
end

//////////////////////////////////////////////////////////////////////////////////
// MODULE
//////////////////////////////////////////////////////////////////////////////////

always @(posedge i_clk) begin
  r_data_valid <= i_valid;
  if (i_valid) begin
    r_data0_r    <= i_data1_r;
    r_data0_i    <= i_data1_i;
    r_data1_r    <= i_data2_r;
    r_data1_i    <= i_data2_i;
  end
end

//-------------------------------------------------------
btfly_2 #(
    .NB_INPUT (NB_INPUT)
) u_btfly2 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .i_data0_r(r_data0_r),
    .i_data0_i(r_data0_i),
    .i_data1_r(r_data1_r),
    .i_data1_i(r_data1_i),
    .o_data0_r(w_bt0_r),
    .o_data0_i(w_bt0_i),
    .o_data1_r(w_bt1_r),
    .o_data1_i(w_bt1_i)
);

//-------------------------------------------------------
assign w_ds0_r = w_bt0_r;
assign w_ds0_i = w_bt0_i;

assign w_pre_ds1_r = (i_inverse) ? -w_bt1_i : w_bt1_i;
assign w_pre_ds1_i = (i_inverse) ? w_bt1_r : -w_bt1_r;
assign w_ds1_r = (r_count == 1'b1) ? w_pre_ds1_r : w_bt1_r;
assign w_ds1_i = (r_count == 1'b1) ? w_pre_ds1_i : w_bt1_i;

//-------------------------------------------------------

ds_switch #(
    .NB(NB_INPUT+1)
) ds_switch_stage1 (
    `ifdef USE_POWER_PINS
    .VPWR       (VPWR),
    .VGND       (VGND),
    `endif
    .i_clk    (i_clk),
    .i_rst_n  (i_rst_n),
    .i_valid  (r_data_valid),
    //----------------------------------------
    .i_data_0r(w_ds0_r),
    .i_data_0i(w_ds0_i),
    .i_data_1r(w_ds1_r),
    .i_data_1i(w_ds1_i),
    //-------------------------------
    .o_valid  (o_valid),
    .o_data_0r(o_data1_r),
    .o_data_0i(o_data1_i),
    .o_data_1r(o_data2_r),
    .o_data_1i(o_data2_i)
);

endmodule
