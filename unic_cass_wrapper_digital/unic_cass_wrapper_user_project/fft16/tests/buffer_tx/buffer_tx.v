//=============================================================================
// Updated: 2026-09-01
// Verification-only wrapper. Chains the output frame buffer to the transmit
// serialiser so the handshake between them can be exercised as one block.
//=============================================================================

module buffer_tx #(
    parameter NB_DATA = 8,
    parameter N_DATA  = 16
) (
    output                          o_data,
    output                          o_ready,
    input                           i_clk,
    input                           i_rstn,
    input                           i_en,
    input                           i_valid,
    input      signed [NB_DATA-1:0] i_data0_re,
    input      signed [NB_DATA-1:0] i_data0_im,
    input      signed [NB_DATA-1:0] i_data1_re,
    input      signed [NB_DATA-1:0] i_data1_im,
    input      signed [NB_DATA-1:0] i_data2_re,
    input      signed [NB_DATA-1:0] i_data2_im,
    input      signed [NB_DATA-1:0] i_data3_re,
    input      signed [NB_DATA-1:0] i_data3_im,
    input      signed [NB_DATA-1:0] i_data4_re,
    input      signed [NB_DATA-1:0] i_data4_im,
    input      signed [NB_DATA-1:0] i_data5_re,
    input      signed [NB_DATA-1:0] i_data5_im,
    input      signed [NB_DATA-1:0] i_data6_re,
    input      signed [NB_DATA-1:0] i_data6_im,
    input      signed [NB_DATA-1:0] i_data7_re,
    input      signed [NB_DATA-1:0] i_data7_im
);

wire signed [NB_DATA-1:0] buf_data_re;
wire signed [NB_DATA-1:0] buf_data_im;
wire                      buf_valid;
wire                      tx_ready;

assign o_ready = tx_ready;

buffer_parallel2serial #(
    .NB_DATA    (NB_DATA)
) u_buffer_parallel2serial (
    .o_data_re  (buf_data_re),
    .o_data_im  (buf_data_im),
    .o_valid    (buf_valid),
    .i_clk      (i_clk),
    .i_rstn     (i_rstn),
    .i_en       (i_en),
    .i_valid    (i_valid),
    .i_tx_ready (tx_ready),
    .i_data0_re (i_data0_re),
    .i_data0_im (i_data0_im),
    .i_data1_re (i_data1_re),
    .i_data1_im (i_data1_im),
    .i_data2_re (i_data2_re),
    .i_data2_im (i_data2_im),
    .i_data3_re (i_data3_re),
    .i_data3_im (i_data3_im),
    .i_data4_re (i_data4_re),
    .i_data4_im (i_data4_im),
    .i_data5_re (i_data5_re),
    .i_data5_im (i_data5_im),
    .i_data6_re (i_data6_re),
    .i_data6_im (i_data6_im),
    .i_data7_re (i_data7_re),
    .i_data7_im (i_data7_im)
);

tx_serializer #(
    .NB_DATA    (NB_DATA),
    .N_DATA     (N_DATA)
) u_tx_serializer (
    .o_data     (o_data),
    .o_ready    (tx_ready),
    .i_clk      (i_clk),
    .i_rstn     (i_rstn),
    .i_valid    (buf_valid),
    .i_data_re  (buf_data_re),
    .i_data_im  (buf_data_im)
);

endmodule
