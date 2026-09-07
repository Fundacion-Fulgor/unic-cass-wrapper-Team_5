//=============================================================================
// Updated: 2026-09-01
// Serial-to-parallel commutator for the radix-2 stage. A 3-deep delay line
// exposes taps 2 samples apart, so every second valid pulse presents the
// pair a[m], a[m+2] of the current group of four.
//=============================================================================

module fft16_shift_r2 #(
    parameter NB_DATA = 8
) (
    `ifdef USE_POWER_PINS
    inout                       VPWR,
    inout                       VGND,
    `endif
    output signed [NB_DATA-1:0] o_data0_re,
    output signed [NB_DATA-1:0] o_data0_im,
    output signed [NB_DATA-1:0] o_data1_re,
    output signed [NB_DATA-1:0] o_data1_im,
    output                      o_valid,
    input                       i_clk,
    input                       i_rstn,
    input                       i_en,
    input                       i_valid,
    input  signed [NB_DATA-1:0] i_data_re,
    input  signed [NB_DATA-1:0] i_data_im
);

localparam CNT_W     = 2;
localparam CNT_FIRST = 2'd2;

reg signed [NB_DATA*3-1:0] data_re_d;
reg signed [NB_DATA*3-1:0] data_im_d;
reg        [CNT_W-1:0]     valid_cnt;
reg                        valid_d;

always @(posedge i_clk) begin
    if (i_en && i_valid) begin
        data_re_d[  NB_DATA-1:0      ] <= i_data_re;
        data_re_d[3*NB_DATA-1:NB_DATA] <= data_re_d[2*NB_DATA-1:0];
        data_im_d[  NB_DATA-1:0      ] <= i_data_im;
        data_im_d[3*NB_DATA-1:NB_DATA] <= data_im_d[2*NB_DATA-1:0];
    end
end

always @(posedge i_clk) begin
    if (!i_rstn) begin
        valid_cnt <= {CNT_W{1'b0}};
        valid_d   <= 1'b0;
    end
    else if (i_en) begin
        if (i_valid) begin
            valid_cnt <= valid_cnt + 1'b1;
            valid_d   <= (valid_cnt >= CNT_FIRST);
        end
        else begin
            valid_d <= 1'b0;
        end
    end
    else begin
        valid_d <= 1'b0;
    end
end

assign o_data1_re = data_re_d[NB_DATA-1:0];
assign o_data1_im = data_im_d[NB_DATA-1:0];
assign o_data0_re = data_re_d[3*NB_DATA-1-:NB_DATA];
assign o_data0_im = data_im_d[3*NB_DATA-1-:NB_DATA];
assign o_valid    = valid_d;

endmodule
