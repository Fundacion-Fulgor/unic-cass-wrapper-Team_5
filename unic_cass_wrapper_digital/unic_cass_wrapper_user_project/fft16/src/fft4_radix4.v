//=============================================================================
// Updated: 2026-09-01
// First radix-4 stage of the FFT16. Takes one decimated group of four samples
// per valid pulse, computes the radix-4 butterfly and applies the twiddle
// factor selected by the group index. Six pipeline stages end to end.
//=============================================================================

module fft4_radix4 #(
    parameter NB_INPUT = 8
) (
    `ifdef USE_POWER_PINS
    inout                        VPWR,
    inout                        VGND,
    `endif
    output                       o_valid,
    output signed [NB_INPUT+1:0] o_data0_re,
    output signed [NB_INPUT+1:0] o_data0_im,
    output signed [NB_INPUT+1:0] o_data1_re,
    output signed [NB_INPUT+1:0] o_data1_im,
    output signed [NB_INPUT+1:0] o_data2_re,
    output signed [NB_INPUT+1:0] o_data2_im,
    output signed [NB_INPUT+1:0] o_data3_re,
    output signed [NB_INPUT+1:0] o_data3_im,
    input                        i_clk,
    input                        i_rstn,
    input                        i_en,
    input                        i_inverse,
    input                        i_valid,
    input  signed [NB_INPUT-1:0] i_data0_re,
    input  signed [NB_INPUT-1:0] i_data0_im,
    input  signed [NB_INPUT-1:0] i_data1_re,
    input  signed [NB_INPUT-1:0] i_data1_im,
    input  signed [NB_INPUT-1:0] i_data2_re,
    input  signed [NB_INPUT-1:0] i_data2_im,
    input  signed [NB_INPUT-1:0] i_data3_re,
    input  signed [NB_INPUT-1:0] i_data3_im
);

localparam NB_TW  = 10;
localparam NBF_TW =  9;
localparam NBF_MUL = 6;

wire signed [NB_TW-1:0]    tw_re [16-1:0];
wire signed [NB_TW-1:0]    tw_im [16-1:0];
wire signed [NB_TW-1:0]    tw0_re;
wire signed [NB_TW-1:0]    tw0_im;
wire signed [NB_TW-1:0]    tw1_re;
wire signed [NB_TW-1:0]    tw1_im;
wire signed [NB_TW-1:0]    tw2_re;
wire signed [NB_TW-1:0]    tw2_im;
wire signed [NB_TW-1:0]    tw3_re;
wire signed [NB_TW-1:0]    tw3_im;

reg  signed [NB_INPUT-1:0] x0_re_d;
reg  signed [NB_INPUT-1:0] x1_re_d;
reg  signed [NB_INPUT-1:0] x2_re_d;
reg  signed [NB_INPUT-1:0] x3_re_d;
reg  signed [NB_INPUT-1:0] x0_im_d;
reg  signed [NB_INPUT-1:0] x1_im_d;
reg  signed [NB_INPUT-1:0] x2_im_d;
reg  signed [NB_INPUT-1:0] x3_im_d;

reg  signed [NB_INPUT+0:0] ev_sum_re_2d;
reg  signed [NB_INPUT+0:0] ev_sub_re_2d;
reg  signed [NB_INPUT+0:0] od_sum_re_2d;
reg  signed [NB_INPUT+0:0] od_sub_re_2d;
reg  signed [NB_INPUT+0:0] ev_sum_im_2d;
reg  signed [NB_INPUT+0:0] ev_sub_im_2d;
reg  signed [NB_INPUT+0:0] od_sum_im_2d;
reg  signed [NB_INPUT+0:0] od_sub_im_2d;

reg  signed [NB_INPUT+1:0] x0_re_3d;
reg  signed [NB_INPUT+1:0] x1_re_3d;
reg  signed [NB_INPUT+1:0] x2_re_3d;
reg  signed [NB_INPUT+1:0] x3_re_3d;
reg  signed [NB_INPUT+1:0] x0_im_3d;
reg  signed [NB_INPUT+1:0] x1_im_3d;
reg  signed [NB_INPUT+1:0] x2_im_3d;
reg  signed [NB_INPUT+1:0] x3_im_3d;

reg  signed [NB_INPUT+1:0] x0_re_4d;
reg  signed [NB_INPUT+1:0] x1_re_4d;
reg  signed [NB_INPUT+1:0] x2_re_4d;
reg  signed [NB_INPUT+1:0] x3_re_4d;
reg  signed [NB_INPUT+1:0] x0_im_4d;
reg  signed [NB_INPUT+1:0] x1_im_4d;
reg  signed [NB_INPUT+1:0] x2_im_4d;
reg  signed [NB_INPUT+1:0] x3_im_4d;

reg  signed [NB_TW-1:0]    tw0_re_4d;
reg  signed [NB_TW-1:0]    tw0_im_4d;
reg  signed [NB_TW-1:0]    tw1_re_4d;
reg  signed [NB_TW-1:0]    tw1_im_4d;
reg  signed [NB_TW-1:0]    tw2_re_4d;
reg  signed [NB_TW-1:0]    tw2_im_4d;
reg  signed [NB_TW-1:0]    tw3_re_4d;
reg  signed [NB_TW-1:0]    tw3_im_4d;

reg         [2-1:0]        m_cnt;
reg         [2-1:0]        m_d;
reg         [2-1:0]        m_2d;
reg         [2-1:0]        m_3d;
wire        [4-1:0]        idx_tw0;
wire        [4-1:0]        idx_tw1;
wire        [4-1:0]        idx_tw2;
wire        [4-1:0]        idx_tw3;

reg                        valid_d;
reg                        valid_2d;
reg                        valid_3d;
reg                        valid_4d;
reg                        valid_5d;
reg                        valid_6d;
reg                        inv_d;
reg                        inv_2d;

assign tw_re[ 0] = 10'h1FF;
assign tw_re[ 1] = 10'h1D9;
assign tw_re[ 2] = 10'h16A;
assign tw_re[ 3] = 10'h0C4;
assign tw_re[ 4] = 10'h000;
assign tw_re[ 5] = 10'h33C;
assign tw_re[ 6] = 10'h296;
assign tw_re[ 7] = 10'h227;
assign tw_re[ 8] = 10'h200;
assign tw_re[ 9] = 10'h227;
assign tw_re[10] = 10'h296;
assign tw_re[11] = 10'h33C;
assign tw_re[12] = 10'h000;
assign tw_re[13] = 10'h0C4;
assign tw_re[14] = 10'h16A;
assign tw_re[15] = 10'h1D9;

assign tw_im[ 0] = (i_inverse) ? 10'h000 : 10'h000;
assign tw_im[ 1] = (i_inverse) ? 10'h0C4 : 10'h33C;
assign tw_im[ 2] = (i_inverse) ? 10'h16A : 10'h296;
assign tw_im[ 3] = (i_inverse) ? 10'h1D9 : 10'h227;
assign tw_im[ 4] = (i_inverse) ? 10'h1FF : 10'h200;
assign tw_im[ 5] = (i_inverse) ? 10'h1D9 : 10'h227;
assign tw_im[ 6] = (i_inverse) ? 10'h16A : 10'h296;
assign tw_im[ 7] = (i_inverse) ? 10'h0C4 : 10'h33C;
assign tw_im[ 8] = (i_inverse) ? 10'h000 : 10'h000;
assign tw_im[ 9] = (i_inverse) ? 10'h33C : 10'h0C4;
assign tw_im[10] = (i_inverse) ? 10'h296 : 10'h16A;
assign tw_im[11] = (i_inverse) ? 10'h227 : 10'h1D9;
assign tw_im[12] = (i_inverse) ? 10'h200 : 10'h1FF;
assign tw_im[13] = (i_inverse) ? 10'h227 : 10'h1D9;
assign tw_im[14] = (i_inverse) ? 10'h296 : 10'h16A;
assign tw_im[15] = (i_inverse) ? 10'h33C : 10'h0C4;

always @(posedge i_clk) begin
    if (!i_rstn) begin
        valid_d  <= 1'b0;
        valid_2d <= 1'b0;
        valid_3d <= 1'b0;
        valid_4d <= 1'b0;
        valid_5d <= 1'b0;
        valid_6d <= 1'b0;
        inv_d    <= 1'b0;
        inv_2d   <= 1'b0;
    end
    else if (i_en) begin
        valid_6d <= valid_5d;
        valid_5d <= valid_4d;
        valid_4d <= valid_3d;
        valid_3d <= valid_2d;
        valid_2d <= valid_d;
        valid_d  <= i_valid;
        inv_2d   <= inv_d;
        inv_d    <= i_inverse;
    end
end

always @(posedge i_clk) begin
    if (i_en && i_valid) begin
        x0_re_d <= i_data0_re;
        x0_im_d <= i_data0_im;
        x1_re_d <= i_data1_re;
        x1_im_d <= i_data1_im;
        x2_re_d <= i_data2_re;
        x2_im_d <= i_data2_im;
        x3_re_d <= i_data3_re;
        x3_im_d <= i_data3_im;
    end
end

always @(posedge i_clk) begin
    if (i_en && valid_d) begin
        ev_sum_re_2d <= x0_re_d + x2_re_d;
        ev_sum_im_2d <= x0_im_d + x2_im_d;
        ev_sub_re_2d <= x0_re_d - x2_re_d;
        ev_sub_im_2d <= x0_im_d - x2_im_d;
        od_sum_re_2d <= x1_re_d + x3_re_d;
        od_sum_im_2d <= x1_im_d + x3_im_d;
        od_sub_re_2d <= x1_re_d - x3_re_d;
        od_sub_im_2d <= x1_im_d - x3_im_d;
    end
end

always @(posedge i_clk) begin
    if (i_en && valid_2d) begin
        x0_re_3d <= ev_sum_re_2d + od_sum_re_2d;
        x0_im_3d <= ev_sum_im_2d + od_sum_im_2d;
        x2_re_3d <= ev_sum_re_2d - od_sum_re_2d;
        x2_im_3d <= ev_sum_im_2d - od_sum_im_2d;
        if (inv_2d) begin
            x1_re_3d <= ev_sub_re_2d - od_sub_im_2d;
            x1_im_3d <= ev_sub_im_2d + od_sub_re_2d;
            x3_re_3d <= ev_sub_re_2d + od_sub_im_2d;
            x3_im_3d <= ev_sub_im_2d - od_sub_re_2d;
        end
        else begin
            x1_re_3d <= ev_sub_re_2d + od_sub_im_2d;
            x1_im_3d <= ev_sub_im_2d - od_sub_re_2d;
            x3_re_3d <= ev_sub_re_2d - od_sub_im_2d;
            x3_im_3d <= ev_sub_im_2d + od_sub_re_2d;
        end
    end
end

always @(posedge i_clk) begin
    if (!i_rstn) begin
        m_cnt <= 2'b00;
        m_d   <= 2'b00;
        m_2d  <= 2'b00;
        m_3d  <= 2'b00;
    end
    else if (i_en) begin
        if (i_valid) begin
            m_cnt <= m_cnt + 1'b1;
        end
        m_d  <= m_cnt;
        m_2d <= m_d;
        m_3d <= m_2d;
    end
end

assign idx_tw0 = 4'd0;
assign idx_tw1 = {2'b00, m_3d};
assign idx_tw2 = {1'b0, m_3d, 1'b0};
assign idx_tw3 = {2'b00, m_3d} + {1'b0, m_3d, 1'b0};

assign tw0_re = tw_re[idx_tw0];
assign tw0_im = tw_im[idx_tw0];
assign tw1_re = tw_re[idx_tw1];
assign tw1_im = tw_im[idx_tw1];
assign tw2_re = tw_re[idx_tw2];
assign tw2_im = tw_im[idx_tw2];
assign tw3_re = tw_re[idx_tw3];
assign tw3_im = tw_im[idx_tw3];

always @(posedge i_clk) begin
    if (i_en && valid_3d) begin
        tw0_re_4d <= tw0_re;
        tw0_im_4d <= tw0_im;
        tw1_re_4d <= tw1_re;
        tw1_im_4d <= tw1_im;
        tw2_re_4d <= tw2_re;
        tw2_im_4d <= tw2_im;
        tw3_re_4d <= tw3_re;
        tw3_im_4d <= tw3_im;

        x0_re_4d  <= x0_re_3d;
        x0_im_4d  <= x0_im_3d;
        x1_re_4d  <= x1_re_3d;
        x1_im_4d  <= x1_im_3d;
        x2_re_4d  <= x2_re_3d;
        x2_im_4d  <= x2_im_3d;
        x3_re_4d  <= x3_re_3d;
        x3_im_4d  <= x3_im_3d;
    end
end

fft4_mul #(
    .NB_DATA   (NB_INPUT+2),
    .NB_TW     (NB_TW),
    .NBF_TW    (NBF_TW),
    .NBF_OUT   (NBF_MUL)
) u_fft4_mul_0 (
    `ifdef USE_POWER_PINS
    .VPWR      (VPWR),
    .VGND      (VGND),
    `endif
    .o_data_re (o_data0_re),
    .o_data_im (o_data0_im),
    .i_clk     (i_clk),
    .i_en      (i_en),
    .i_data_re (x0_re_4d),
    .i_data_im (x0_im_4d),
    .i_tw_re   (tw0_re_4d),
    .i_tw_im   (tw0_im_4d)
);

fft4_mul #(
    .NB_DATA   (NB_INPUT+2),
    .NB_TW     (NB_TW),
    .NBF_TW    (NBF_TW),
    .NBF_OUT   (NBF_MUL)
) u_fft4_mul_1 (
    `ifdef USE_POWER_PINS
    .VPWR      (VPWR),
    .VGND      (VGND),
    `endif
    .o_data_re (o_data1_re),
    .o_data_im (o_data1_im),
    .i_clk     (i_clk),
    .i_en      (i_en),
    .i_data_re (x1_re_4d),
    .i_data_im (x1_im_4d),
    .i_tw_re   (tw1_re_4d),
    .i_tw_im   (tw1_im_4d)
);

fft4_mul #(
    .NB_DATA   (NB_INPUT+2),
    .NB_TW     (NB_TW),
    .NBF_TW    (NBF_TW),
    .NBF_OUT   (NBF_MUL)
) u_fft4_mul_2 (
    `ifdef USE_POWER_PINS
    .VPWR      (VPWR),
    .VGND      (VGND),
    `endif
    .o_data_re (o_data2_re),
    .o_data_im (o_data2_im),
    .i_clk     (i_clk),
    .i_en      (i_en),
    .i_data_re (x2_re_4d),
    .i_data_im (x2_im_4d),
    .i_tw_re   (tw2_re_4d),
    .i_tw_im   (tw2_im_4d)
);

fft4_mul #(
    .NB_DATA   (NB_INPUT+2),
    .NB_TW     (NB_TW),
    .NBF_TW    (NBF_TW),
    .NBF_OUT   (NBF_MUL)
) u_fft4_mul_3 (
    `ifdef USE_POWER_PINS
    .VPWR      (VPWR),
    .VGND      (VGND),
    `endif
    .o_data_re (o_data3_re),
    .o_data_im (o_data3_im),
    .i_clk     (i_clk),
    .i_en      (i_en),
    .i_data_re (x3_re_4d),
    .i_data_im (x3_im_4d),
    .i_tw_re   (tw3_re_4d),
    .i_tw_im   (tw3_im_4d)
);

assign o_valid = valid_6d;

endmodule
