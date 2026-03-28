module fft16_shift_r4 #(
    parameter NB_DATA   = 8
) (
    `ifdef USE_POWER_PINS
    inout                       VPWR,
    inout                       VGND,
    `endif
    input                       i_clk,
    input                       i_rst_n,   // added
    input                       i_clk_en,
    ///////////////////// INPUTS  /////////////////////
    input                       i_valid,
    input  signed [NB_DATA-1:0] i_data_re,
    input  signed [NB_DATA-1:0] i_data_im,
    ///////////////////// OUTPUTS /////////////////////
    output signed [NB_DATA-1:0] o_data0_re,
    output signed [NB_DATA-1:0] o_data0_im,
    output signed [NB_DATA-1:0] o_data1_re,
    output signed [NB_DATA-1:0] o_data1_im,
    output signed [NB_DATA-1:0] o_data2_re,
    output signed [NB_DATA-1:0] o_data2_im,
    output signed [NB_DATA-1:0] o_data3_re,
    output signed [NB_DATA-1:0] o_data3_im,
    output                      o_valid
);

reg [NB_DATA*13-1:0] data_re_q;
reg [NB_DATA*13-1:0] data_im_q;
reg [        13-1:0] valid_q;
reg                  last_valid;
integer k;

// valid_q now resets so it cannot retain stale 1-bits across tests.
// Without this, valid_q[12]=1 from a previous block causes o_valid to
// fire on the very first new i_valid pulse, mixing stale data into the
// fft4_radix4 input.
always @(posedge i_clk) begin
    if (!i_rst_n) begin
        valid_q <= 13'b0;
    end
    else if (i_clk_en && i_valid) begin
        data_re_q[   NB_DATA-1:0      ] <= i_data_re;
        data_im_q[   NB_DATA-1:0      ] <= i_data_im;
        valid_q  [   0]                 <= i_valid;
        for (k = 1; k < 13; k = k + 1) begin
            data_re_q[k*NB_DATA +: NB_DATA] <= data_re_q[(k-1)*NB_DATA +: NB_DATA];
            data_im_q[k*NB_DATA +: NB_DATA] <= data_im_q[(k-1)*NB_DATA +: NB_DATA];
            valid_q[k]                      <= valid_q[k-1];
        end
    end
end

always @(posedge i_clk) begin
    last_valid <= i_valid;
end

assign o_data3_re = data_re_q[NB_DATA-1:0];
assign o_data3_im = data_im_q[NB_DATA-1:0];
assign o_data2_re = data_re_q[ 5*NB_DATA-1-:NB_DATA];
assign o_data2_im = data_im_q[ 5*NB_DATA-1-:NB_DATA];
assign o_data1_re = data_re_q[ 9*NB_DATA-1-:NB_DATA];
assign o_data1_im = data_im_q[ 9*NB_DATA-1-:NB_DATA];
assign o_data0_re = data_re_q[13*NB_DATA-1-:NB_DATA];
assign o_data0_im = data_im_q[13*NB_DATA-1-:NB_DATA];
assign o_valid    = valid_q[12] & last_valid;

endmodule