module buffer_parallel2serial #(
    parameter NB_DATA = 8
) (
    `ifdef USE_POWER_PINS
    inout                           VPWR,
    inout                           VGND,
    `endif
    input                           i_clk,
    input                           i_rst_n,
    input                           i_clk_en,
    input                           i_valid,
    input                           i_tx_ready,
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
    input      signed [NB_DATA-1:0] i_data7_im,
    output reg signed [NB_DATA-1:0] o_data_re,
    output reg signed [NB_DATA-1:0] o_data_im,
    output reg                      o_valid
);

reg signed [NB_DATA-1:0] mem_re [0:15];
reg signed [NB_DATA-1:0] mem_im [0:15];

localparam S_LOADING  = 2'd0;
localparam S_WAIT_RDY = 2'd1;
localparam S_WAIT_BSY = 2'd2;

reg [1:0] state;
reg       batch_count;
reg [3:0] read_ptr;

always @(posedge i_clk) begin
    if (!i_rst_n) begin
        state       <= S_LOADING;
        batch_count <= 1'b0;
        read_ptr    <= 4'd0;
        o_valid     <= 1'b0;
        o_data_re   <= 0;
        o_data_im   <= 0;
    end
    else if (i_clk_en) begin
        case (state)
            S_LOADING: begin
                o_valid <= 1'b0;
                if (i_valid) begin
                    mem_re[{batch_count, 3'd0}] <= i_data0_re; mem_im[{batch_count, 3'd0}] <= i_data0_im;
                    mem_re[{batch_count, 3'd1}] <= i_data1_re; mem_im[{batch_count, 3'd1}] <= i_data1_im;
                    mem_re[{batch_count, 3'd2}] <= i_data2_re; mem_im[{batch_count, 3'd2}] <= i_data2_im;
                    mem_re[{batch_count, 3'd3}] <= i_data3_re; mem_im[{batch_count, 3'd3}] <= i_data3_im;
                    mem_re[{batch_count, 3'd4}] <= i_data4_re; mem_im[{batch_count, 3'd4}] <= i_data4_im;
                    mem_re[{batch_count, 3'd5}] <= i_data5_re; mem_im[{batch_count, 3'd5}] <= i_data5_im;
                    mem_re[{batch_count, 3'd6}] <= i_data6_re; mem_im[{batch_count, 3'd6}] <= i_data6_im;
                    mem_re[{batch_count, 3'd7}] <= i_data7_re; mem_im[{batch_count, 3'd7}] <= i_data7_im;
                    if (batch_count == 1'b1) begin
                        batch_count <= 1'b0;
                        read_ptr    <= 4'd0;
                        state       <= S_WAIT_RDY;
                    end else begin
                        batch_count <= batch_count + 1'b1;
                    end
                end
            end
            S_WAIT_RDY: begin
                o_valid <= 1'b0;
                if (i_tx_ready) begin
                    o_data_re <= mem_re[read_ptr];
                    o_data_im <= mem_im[read_ptr];
                    o_valid   <= 1'b1;
                    state     <= S_WAIT_BSY;
                end
            end
            S_WAIT_BSY: begin
                o_valid <= 1'b0;
                if (!i_tx_ready) begin
                    if (read_ptr == 4'd15) begin
                        read_ptr <= 4'd0;
                        state    <= S_LOADING;
                    end else begin
                        read_ptr <= read_ptr + 1'b1;
                        state    <= S_WAIT_RDY;
                    end
                end
            end
            default: state <= S_LOADING;
        endcase
    end
end

endmodule