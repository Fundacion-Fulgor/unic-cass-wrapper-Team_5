//=============================================================================
// Updated: 2026-09-01
// Input deserialiser. Detects the rising edge that starts a block and then
// collects N_DATA words of 2*NB_DATA bits, emitting one complex sample per
// completed word.
//=============================================================================

module rx_serializer #(
    parameter NB_DATA = 8,
    parameter N_DATA  = 16
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
    input                           i_data
);

localparam TOTAL_BITS = 2 * NB_DATA;
localparam NB_CNT     = 5;
localparam SAMP_W     = $clog2(N_DATA);

localparam S_IDLE = 1'b0;
localparam S_RECV = 1'b1;

reg                  current_state;
reg                  next_state;
reg [NB_CNT-1:0]     current_cnt;
reg [NB_CNT-1:0]     next_cnt;
reg [TOTAL_BITS-1:0] current_shift;
reg [TOTAL_BITS-1:0] next_shift;
reg [SAMP_W-1:0]     current_samp;
reg [SAMP_W-1:0]     next_samp;

reg                  data_d;
wire                 start_detected;

always @(posedge i_clk) begin
    if (!i_rstn) begin
        data_d <= 1'b0;
    end
    else begin
        data_d <= i_data;
    end
end

assign start_detected = i_data && !data_d;

always @(posedge i_clk) begin
    if (!i_rstn) begin
        current_state <= S_IDLE;
        current_cnt   <= {NB_CNT{1'b0}};
        current_shift <= {TOTAL_BITS{1'b0}};
        current_samp  <= {SAMP_W{1'b0}};
        o_valid       <= 1'b0;
        o_data_re     <= {NB_DATA{1'b0}};
        o_data_im     <= {NB_DATA{1'b0}};
    end
    else begin
        current_state <= next_state;
        current_cnt   <= next_cnt;
        current_shift <= next_shift;
        current_samp  <= next_samp;
        if ((current_state == S_RECV) && (current_cnt == TOTAL_BITS - 1)) begin
            o_data_re <= next_shift[TOTAL_BITS-1 -: NB_DATA];
            o_data_im <= next_shift[NB_DATA-1    -: NB_DATA];
            o_valid   <= 1'b1;
        end
        else begin
            o_valid <= 1'b0;
        end
    end
end

always @(*) begin
    next_state = current_state;
    next_cnt   = current_cnt;
    next_shift = {current_shift[TOTAL_BITS-2:0], i_data};
    next_samp  = current_samp;

    case (current_state)
        S_IDLE: begin
            next_cnt  = {NB_CNT{1'b0}};
            next_samp = {SAMP_W{1'b0}};
            if (start_detected) begin
                next_state = S_RECV;
            end
        end

        S_RECV: begin
            if (current_cnt == TOTAL_BITS - 1) begin
                next_cnt = {NB_CNT{1'b0}};
                if (current_samp == (N_DATA - 1)) begin
                    next_state = S_IDLE;
                end
                else begin
                    next_samp = current_samp + 1'b1;
                end
            end
            else begin
                next_cnt = current_cnt + 1'b1;
            end
        end

        default: begin
            next_state = S_IDLE;
        end
    endcase
end

endmodule
