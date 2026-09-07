//=============================================================================
// Updated: 2026-09-01
// Serial-to-parallel commutator for the radix-4 stage. A 13-deep delay line
// exposes taps 4 samples apart, so every fourth valid pulse presents the
// group x[m], x[m+4], x[m+8], x[m+12] of the current 16-sample block.
//=============================================================================

module fft16_shift_r4 #(
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
    output signed [NB_DATA-1:0] o_data2_re,
    output signed [NB_DATA-1:0] o_data2_im,
    output signed [NB_DATA-1:0] o_data3_re,
    output signed [NB_DATA-1:0] o_data3_im,
    output                      o_valid,
    input                       i_clk,
    input                       i_rstn,
    input                       i_en,
    input                       i_valid,
    input  signed [NB_DATA-1:0] i_data_re,
    input  signed [NB_DATA-1:0] i_data_im
);

localparam N_TAP     = 13;
localparam CNT_W     =  4;
localparam CNT_FIRST = 4'd12;

reg [NB_DATA*N_TAP-1:0] data_re_d;
reg [NB_DATA*N_TAP-1:0] data_im_d;
reg [CNT_W-1:0]         valid_cnt;
reg                     valid_d;
integer k;

always @(posedge i_clk) begin
    if (i_en && i_valid) begin
        data_re_d[NB_DATA-1:0] <= i_data_re;
        data_im_d[NB_DATA-1:0] <= i_data_im;
        for (k = 1; k < N_TAP; k = k + 1) begin
            data_re_d[k*NB_DATA +: NB_DATA] <= data_re_d[(k-1)*NB_DATA +: NB_DATA];
            data_im_d[k*NB_DATA +: NB_DATA] <= data_im_d[(k-1)*NB_DATA +: NB_DATA];
        end
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

assign o_data3_re = data_re_d[NB_DATA-1:0];
assign o_data3_im = data_im_d[NB_DATA-1:0];
assign o_data2_re = data_re_d[ 5*NB_DATA-1-:NB_DATA];
assign o_data2_im = data_im_d[ 5*NB_DATA-1-:NB_DATA];
assign o_data1_re = data_re_d[ 9*NB_DATA-1-:NB_DATA];
assign o_data1_im = data_im_d[ 9*NB_DATA-1-:NB_DATA];
assign o_data0_re = data_re_d[13*NB_DATA-1-:NB_DATA];
assign o_data0_im = data_im_d[13*NB_DATA-1-:NB_DATA];
assign o_valid    = valid_d;

endmodule
