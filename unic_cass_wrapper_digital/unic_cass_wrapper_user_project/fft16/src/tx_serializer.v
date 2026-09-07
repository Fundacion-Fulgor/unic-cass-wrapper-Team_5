//=============================================================================
// Updated: 2026-09-01
// Output serialiser. Sends each complex sample as 2*NB_DATA bits, prefixed by
// a single start bit on the first sample of every N_DATA block. o_ready marks
// the cycles in which a new sample can be accepted.
//=============================================================================

module tx_serializer #(
    parameter NB_DATA = 8,
    parameter N_DATA  = 16
) (
    `ifdef USE_POWER_PINS
    inout                       VPWR,
    inout                       VGND,
    `endif
    output reg                  o_data,
    output                      o_ready,
    input                       i_clk,
    input                       i_rstn,
    input                       i_valid,
    input  signed [NB_DATA-1:0] i_data_re,
    input  signed [NB_DATA-1:0] i_data_im
);

localparam TOTAL_BITS = 2 * NB_DATA;
localparam CNT_W      = 5;
localparam SAMP_W     = $clog2(N_DATA);

localparam [1:0] S_IDLE  = 2'd0;
localparam [1:0] S_START = 2'd1;
localparam [1:0] S_SEND  = 2'd2;

reg [1:0]            current_state;
reg [1:0]            next_state;
reg [CNT_W-1:0]      current_cnt;
reg [CNT_W-1:0]      next_cnt;
reg [TOTAL_BITS-1:0] current_shift;
reg [TOTAL_BITS-1:0] next_shift;
reg [SAMP_W-1:0]     current_samp;
reg [SAMP_W-1:0]     next_samp;
reg                  data;

assign o_ready = (current_state == S_IDLE);

always @(posedge i_clk) begin
    if (!i_rstn) begin
        current_state <= S_IDLE;
        current_cnt   <= {CNT_W{1'b0}};
        current_shift <= {TOTAL_BITS{1'b0}};
        current_samp  <= {SAMP_W{1'b0}};
        o_data        <= 1'b0;
    end
    else begin
        current_state <= next_state;
        current_cnt   <= next_cnt;
        current_shift <= next_shift;
        current_samp  <= next_samp;
        o_data        <= data;
    end
end

always @(*) begin
    next_state = current_state;
    next_cnt   = current_cnt;
    next_shift = current_shift;
    next_samp  = current_samp;
    data       = 1'b0;

    case (current_state)
        S_IDLE: begin
            if (i_valid) begin
                next_shift = {i_data_re, i_data_im};
                next_cnt   = TOTAL_BITS - 1;
                if (current_samp == {SAMP_W{1'b0}}) begin
                    next_state = S_START;
                end
                else begin
                    next_state = S_SEND;
                end
            end
        end

        S_START: begin
            data       = 1'b1;
            next_state = S_SEND;
        end

        S_SEND: begin
            data       = current_shift[TOTAL_BITS-1];
            next_shift = {current_shift[TOTAL_BITS-2:0], 1'b0};
            if (current_cnt == {CNT_W{1'b0}}) begin
                next_state = S_IDLE;
                next_samp  = (current_samp == (N_DATA - 1)) ? {SAMP_W{1'b0}}
                                                                  : current_samp + 1'b1;
            end
            else begin
                next_cnt = current_cnt - 1'b1;
            end
        end

        default: begin
            next_state = S_IDLE;
        end
    endcase
end

endmodule
