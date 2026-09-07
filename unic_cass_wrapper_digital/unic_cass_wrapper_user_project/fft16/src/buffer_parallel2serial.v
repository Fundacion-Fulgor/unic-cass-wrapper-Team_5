//=============================================================================
// Updated: 2026-09-01
// Output frame buffer. Collects two batches of eight complex results into a
// 16-word memory and then hands them one at a time to the transmitter,
// following its ready/busy handshake.
//=============================================================================

module buffer_parallel2serial #(
    parameter NB_DATA = 8
) (
    `ifdef USE_POWER_PINS
    inout                           VPWR,
    inout                           VGND,
    `endif
    output reg signed [NB_DATA-1:0] o_data_re,
    output reg signed [NB_DATA-1:0] o_data_im,
    output reg                      o_valid,
    input                           i_clk,
    input                           i_rstn,
    input                           i_en,
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
    input      signed [NB_DATA-1:0] i_data7_im
);

localparam [1:0] S_LOADING  = 2'd0;
localparam [1:0] S_WAIT_RDY = 2'd1;
localparam [1:0] S_WAIT_BSY = 2'd2;

reg signed [NB_DATA-1:0] mem_re [0:15];
reg signed [NB_DATA-1:0] mem_im [0:15];

reg  [1:0] current_state;
reg  [1:0] next_state;
reg        batch_count;
reg  [3:0] read_ptr;

always @(*) begin
    next_state = current_state;
    case (current_state)
        S_LOADING: begin
            if (i_valid && (batch_count == 1'b1)) begin
                next_state = S_WAIT_RDY;
            end
        end
        S_WAIT_RDY: begin
            if (i_tx_ready) begin
                next_state = S_WAIT_BSY;
            end
        end
        S_WAIT_BSY: begin
            if (!i_tx_ready) begin
                next_state = (read_ptr == 4'd15) ? S_LOADING : S_WAIT_RDY;
            end
        end
        default: begin
            next_state = S_LOADING;
        end
    endcase
end

always @(posedge i_clk) begin
    if (!i_rstn) begin
        current_state <= S_LOADING;
    end
    else if (i_en) begin
        current_state <= next_state;
    end
end

always @(posedge i_clk) begin
    if (!i_rstn) begin
        batch_count <= 1'b0;
        read_ptr    <= 4'd0;
        o_valid     <= 1'b0;
        o_data_re   <= {NB_DATA{1'b0}};
        o_data_im   <= {NB_DATA{1'b0}};
    end
    else if (i_en) begin
        o_valid <= 1'b0;
        case (current_state)
            S_LOADING: begin
                if (i_valid) begin
                    mem_re[{batch_count, 3'd0}] <= i_data0_re;
                    mem_im[{batch_count, 3'd0}] <= i_data0_im;
                    mem_re[{batch_count, 3'd1}] <= i_data1_re;
                    mem_im[{batch_count, 3'd1}] <= i_data1_im;
                    mem_re[{batch_count, 3'd2}] <= i_data2_re;
                    mem_im[{batch_count, 3'd2}] <= i_data2_im;
                    mem_re[{batch_count, 3'd3}] <= i_data3_re;
                    mem_im[{batch_count, 3'd3}] <= i_data3_im;
                    mem_re[{batch_count, 3'd4}] <= i_data4_re;
                    mem_im[{batch_count, 3'd4}] <= i_data4_im;
                    mem_re[{batch_count, 3'd5}] <= i_data5_re;
                    mem_im[{batch_count, 3'd5}] <= i_data5_im;
                    mem_re[{batch_count, 3'd6}] <= i_data6_re;
                    mem_im[{batch_count, 3'd6}] <= i_data6_im;
                    mem_re[{batch_count, 3'd7}] <= i_data7_re;
                    mem_im[{batch_count, 3'd7}] <= i_data7_im;
                    if (batch_count == 1'b1) begin
                        batch_count <= 1'b0;
                        read_ptr    <= 4'd0;
                    end
                    else begin
                        batch_count <= batch_count + 1'b1;
                    end
                end
            end
            S_WAIT_RDY: begin
                if (i_tx_ready) begin
                    o_data_re <= mem_re[read_ptr];
                    o_data_im <= mem_im[read_ptr];
                    o_valid   <= 1'b1;
                end
            end
            S_WAIT_BSY: begin
                if (!i_tx_ready) begin
                    read_ptr <= (read_ptr == 4'd15) ? 4'd0 : read_ptr + 1'b1;
                end
            end
            default: begin
                read_ptr <= 4'd0;
            end
        endcase
    end
end

endmodule
