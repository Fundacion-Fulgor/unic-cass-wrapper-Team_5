module fft4_radix4 #(
    parameter NB_INPUT  = 8
)(
    `ifdef USE_POWER_PINS
    inout                        VPWR,  // Common digital supply
    inout                        VGND,  // Common digital ground
    `endif
    input                        i_clk,
    input                        i_rst_n,
    input                        i_inverse,
    input                        i_enable,
    input                        i_valid,
    ///////////////////// INPUTS  /////////////////////
    input  signed [NB_INPUT-1:0] i_data0_re,
    input  signed [NB_INPUT-1:0] i_data0_im,
    input  signed [NB_INPUT-1:0] i_data1_re,
    input  signed [NB_INPUT-1:0] i_data1_im,
    input  signed [NB_INPUT-1:0] i_data2_re,
    input  signed [NB_INPUT-1:0] i_data2_im,
    input  signed [NB_INPUT-1:0] i_data3_re,
    input  signed [NB_INPUT-1:0] i_data3_im,
    ///////////////////// OUTPUTS /////////////////////
    output signed [NB_INPUT+1:0] o_data0_re,
    output signed [NB_INPUT+1:0] o_data0_im,
    output signed [NB_INPUT+1:0] o_data1_re,
    output signed [NB_INPUT+1:0] o_data1_im,
    output signed [NB_INPUT+1:0] o_data2_re,
    output signed [NB_INPUT+1:0] o_data2_im,
    output signed [NB_INPUT+1:0] o_data3_re,
    output signed [NB_INPUT+1:0] o_data3_im,
    output                       o_valid
);

///////////////////////////////////////////////////////////////////////////////
// WIRE AND REGISTER
///////////////////////////////////////////////////////////////////////////////

localparam NB_TW  = 10;
localparam NBF_TW =  9;

wire signed [   NB_TW-1:0] w_tw_re [16-1:0];
wire signed [   NB_TW-1:0] w_tw_im [16-1:0];
wire signed [   NB_TW-1:0] tw0_re;
wire signed [   NB_TW-1:0] tw0_im;
wire signed [   NB_TW-1:0] tw1_re;
wire signed [   NB_TW-1:0] tw1_im;
wire signed [   NB_TW-1:0] tw2_re;
wire signed [   NB_TW-1:0] tw2_im;
wire signed [   NB_TW-1:0] tw3_re;
wire signed [   NB_TW-1:0] tw3_im;

reg  signed [NB_INPUT-1:0] r_x0_re;
reg  signed [NB_INPUT-1:0] r_x1_re;
reg  signed [NB_INPUT-1:0] r_x2_re;
reg  signed [NB_INPUT-1:0] r_x3_re;
reg  signed [NB_INPUT-1:0] r_x0_im;
reg  signed [NB_INPUT-1:0] r_x1_im;
reg  signed [NB_INPUT-1:0] r_x2_im;
reg  signed [NB_INPUT-1:0] r_x3_im;

reg  signed [NB_INPUT+0:0] s1_ev_sum_re;
reg  signed [NB_INPUT+0:0] s1_ev_sub_re;
reg  signed [NB_INPUT+0:0] s1_od_sum_re;
reg  signed [NB_INPUT+0:0] s1_od_sub_re;
reg  signed [NB_INPUT+0:0] s1_ev_sum_im;
reg  signed [NB_INPUT+0:0] s1_ev_sub_im;
reg  signed [NB_INPUT+0:0] s1_od_sum_im;
reg  signed [NB_INPUT+0:0] s1_od_sub_im;

reg  signed [NB_INPUT+1:0] s2_x0_re;
reg  signed [NB_INPUT+1:0] s2_x1_re;
reg  signed [NB_INPUT+1:0] s2_x2_re;
reg  signed [NB_INPUT+1:0] s2_x3_re;
reg  signed [NB_INPUT+1:0] s2_x0_im;
reg  signed [NB_INPUT+1:0] s2_x1_im;
reg  signed [NB_INPUT+1:0] s2_x2_im;
reg  signed [NB_INPUT+1:0] s2_x3_im;

reg         [       2-1:0] r_m_cnt;
reg         [       2-1:0] m_q;
reg         [       2-1:0] m_2q;
reg         [       2-1:0] m_3q;
wire        [       4-1:0] idx_tw0;
wire        [       4-1:0] idx_tw1;
wire        [       4-1:0] idx_tw2;
wire        [       4-1:0] idx_tw3;

reg                        valid_q;
reg                        valid_2q;
reg                        valid_3q;
reg                        valid_4q;
reg                        inv_q;
reg                        inv_2q;
reg                        inv_3q;




///////////////////////////////////////////////////////////////////////////////
// CL
///////////////////////////////////////////////////////////////////////////////

assign w_tw_re[ 0] = 10'h1FF;
assign w_tw_re[ 1] = 10'h1D9;
assign w_tw_re[ 2] = 10'h16A;
assign w_tw_re[ 3] = 10'h0C4;
assign w_tw_re[ 4] = 10'h000;
assign w_tw_re[ 5] = 10'h33C;
assign w_tw_re[ 6] = 10'h296;
assign w_tw_re[ 7] = 10'h227;
assign w_tw_re[ 8] = 10'h200;
assign w_tw_re[ 9] = 10'h227;
assign w_tw_re[10] = 10'h296;
assign w_tw_re[11] = 10'h33C;
assign w_tw_re[12] = 10'h000;
assign w_tw_re[13] = 10'h0C4;
assign w_tw_re[14] = 10'h16A;
assign w_tw_re[15] = 10'h1D9;

assign w_tw_im[ 0] = (i_inverse)? 10'h000 : 10'h000;
assign w_tw_im[ 1] = (i_inverse)? 10'h0C4 : 10'h33C;
assign w_tw_im[ 2] = (i_inverse)? 10'h16A : 10'h296;
assign w_tw_im[ 3] = (i_inverse)? 10'h1D9 : 10'h227;
assign w_tw_im[ 4] = (i_inverse)? 10'h1FF : 10'h200;
assign w_tw_im[ 5] = (i_inverse)? 10'h1D9 : 10'h227;
assign w_tw_im[ 6] = (i_inverse)? 10'h16A : 10'h296;
assign w_tw_im[ 7] = (i_inverse)? 10'h0C4 : 10'h33C;
assign w_tw_im[ 8] = (i_inverse)? 10'h000 : 10'h000;
assign w_tw_im[ 9] = (i_inverse)? 10'h33C : 10'h0C4;
assign w_tw_im[10] = (i_inverse)? 10'h296 : 10'h16A;
assign w_tw_im[11] = (i_inverse)? 10'h227 : 10'h1D9;
assign w_tw_im[12] = (i_inverse)? 10'h200 : 10'h1FF;
assign w_tw_im[13] = (i_inverse)? 10'h227 : 10'h1D9;
assign w_tw_im[14] = (i_inverse)? 10'h296 : 10'h16A;
assign w_tw_im[15] = (i_inverse)? 10'h33C : 10'h0C4;

always @(posedge i_clk) begin
    if (!i_rst_n) begin
        valid_q  <= 1'b0;
        valid_2q <= 1'b0;
        valid_3q <= 1'b0;
        valid_4q <= 1'b0;
        inv_q    <= 1'b0;
        inv_2q   <= 1'b0;
        inv_3q   <= 1'b0;
    end
    else if (i_enable) begin
        valid_4q <= valid_3q;
        valid_3q <= valid_2q;
        valid_2q <= valid_q;
        valid_q  <= i_valid;
        inv_3q   <= inv_2q;
        inv_2q   <= inv_q;
        inv_q    <= i_inverse;
    end
end

always @(posedge i_clk) begin
    if (i_enable && i_valid) begin
        r_x0_re <= i_data0_re;
        r_x0_im <= i_data0_im;
        r_x1_re <= i_data1_re;
        r_x1_im <= i_data1_im;
        r_x2_re <= i_data2_re;
        r_x2_im <= i_data2_im;
        r_x3_re <= i_data3_re;
        r_x3_im <= i_data3_im;
    end
end

always @(posedge i_clk) begin
    if (i_enable && valid_q) begin
        s1_ev_sum_re <= r_x0_re + r_x2_re;
        s1_ev_sum_im <= r_x0_im + r_x2_im;
        s1_ev_sub_re <= r_x0_re - r_x2_re;
        s1_ev_sub_im <= r_x0_im - r_x2_im;

        s1_od_sum_re <= r_x1_re + r_x3_re;
        s1_od_sum_im <= r_x1_im + r_x3_im;
        s1_od_sub_re <= r_x1_re - r_x3_re;
        s1_od_sub_im <= r_x1_im - r_x3_im;
    end
end

always @(posedge i_clk) begin
    if (i_enable && valid_2q) begin
        s2_x0_re <= s1_ev_sum_re + s1_od_sum_re;
        s2_x0_im <= s1_ev_sum_im + s1_od_sum_im;
        s2_x2_re <= s1_ev_sum_re - s1_od_sum_re;
        s2_x2_im <= s1_ev_sum_im - s1_od_sum_im;
        if (inv_2q) begin
            s2_x1_re <= s1_ev_sub_re - s1_od_sub_im;
            s2_x1_im <= s1_ev_sub_im + s1_od_sub_re;
            s2_x3_re <= s1_ev_sub_re + s1_od_sub_im;
            s2_x3_im <= s1_ev_sub_im - s1_od_sub_re;
        end
        else begin
            s2_x1_re <= s1_ev_sub_re + s1_od_sub_im;
            s2_x1_im <= s1_ev_sub_im - s1_od_sub_re;
            s2_x3_re <= s1_ev_sub_re - s1_od_sub_im;
            s2_x3_im <= s1_ev_sub_im + s1_od_sub_re;
        end
    end
end

///////////////////////////////////////////////////////////////////////////////

always @(posedge i_clk) begin
    if (!i_rst_n) begin
        r_m_cnt <= 2'b00;
        m_q     <= 2'b00;
        m_2q    <= 2'b00;
        m_3q    <= 2'b00;
    end else if (i_enable) begin
        if (i_valid) begin
            r_m_cnt <= r_m_cnt + 1'b1;
        end
        m_q  <= r_m_cnt;
        m_2q <= m_q;
        m_3q <= m_2q;
    end
end

assign idx_tw0 = 4'd0;                                 // k=0 -> m * 0
assign idx_tw1 = {2'b00, m_3q};                        // k=1 -> m * 1
assign idx_tw2 = {1'b0, m_3q, 1'b0};                   // k=2 -> m * 2 (shift left)
assign idx_tw3 = {2'b00, m_3q} + {1'b0, m_3q, 1'b0};   // k=3 -> m * 3 (m + 2m)

assign tw0_re = w_tw_re[idx_tw0];
assign tw0_im = w_tw_im[idx_tw0];
assign tw1_re = w_tw_re[idx_tw1];
assign tw1_im = w_tw_im[idx_tw1];
assign tw2_re = w_tw_re[idx_tw2];
assign tw2_im = w_tw_im[idx_tw2];
assign tw3_re = w_tw_re[idx_tw3];
assign tw3_im = w_tw_im[idx_tw3];


fft4_mul u_fft4_mul_0 (

    `ifdef USE_POWER_PINS
        .VPWR       (VPWR),
        .VGND       (VGND),
    `endif

    .i_clk          (i_clk),
    .i_inverse      (i_inverse),
    .i_data_re      (s2_x0_re),
    .i_data_im      (s2_x0_im),
    .i_tw_re        (tw0_re),
    .i_tw_im        (tw0_im),
    .o_data_re      (o_data0_re),
    .o_data_im      (o_data0_im)
);


fft4_mul u_fft4_mul_1 (

    `ifdef USE_POWER_PINS
        .VPWR       (VPWR),
        .VGND       (VGND),
    `endif

    .i_clk          (i_clk),
    .i_inverse      (i_inverse),
    .i_data_re      (s2_x1_re),
    .i_data_im      (s2_x1_im),
    .i_tw_re        (tw1_re),
    .i_tw_im        (tw1_im),
    .o_data_re      (o_data1_re),
    .o_data_im      (o_data1_im)
);

fft4_mul u_fft4_mul_2 (

    `ifdef USE_POWER_PINS
        .VPWR       (VPWR),
        .VGND       (VGND),
    `endif

    .i_clk          (i_clk),
    .i_inverse      (i_inverse),
    .i_data_re      (s2_x2_re),
    .i_data_im      (s2_x2_im),
    .i_tw_re        (tw2_re),
    .i_tw_im        (tw2_im),
    .o_data_re      (o_data2_re),
    .o_data_im      (o_data2_im)
);

fft4_mul u_fft4_mul_3 (

    `ifdef USE_POWER_PINS
        .VPWR       (VPWR),
        .VGND       (VGND),
    `endif

    .i_clk          (i_clk),
    .i_inverse      (i_inverse),
    .i_data_re      (s2_x3_re),
    .i_data_im      (s2_x3_im),
    .i_tw_re        (tw3_re),
    .i_tw_im        (tw3_im),
    .o_data_re      (o_data3_re),
    .o_data_im      (o_data3_im)
);

assign o_valid = valid_4q;

endmodule