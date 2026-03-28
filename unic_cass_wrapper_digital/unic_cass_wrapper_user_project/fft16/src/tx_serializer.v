module tx_serializer #(
    parameter NB_DATA = 8,
    parameter N_DATA  = 16
)(
    `ifdef USE_POWER_PINS
    inout                       VPWR,
    inout                       VGND,
    `endif
    input                       i_clk,
    input                       i_rst_n,
    input                       i_valid,
    input  signed [NB_DATA-1:0] i_data_re,
    input  signed [NB_DATA-1:0] i_data_im,
    output reg                  o_data,
    output                      o_ready
);

localparam TOTAL_BITS = 2 * NB_DATA;
localparam CNT_W      = 5;
localparam SAMP_W     = $clog2(N_DATA);

localparam STATE_IDLE  = 0;
localparam STATE_START = 1;
localparam STATE_SEND  = 2;

reg [1:0]            current_state, next_state;
reg [CNT_W-1:0]      current_cnt,   next_cnt;
reg [TOTAL_BITS-1:0] current_shift,  next_shift;
reg [SAMP_W-1:0]     current_samp,   next_samp;
reg                  data;

assign o_ready = (current_state == STATE_IDLE);

always @(posedge i_clk or negedge i_rst_n) begin
    if (!i_rst_n) begin
        current_state <= STATE_IDLE;
        current_cnt   <= 0;
        current_shift <= 0;
        current_samp  <= 0;
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
        STATE_IDLE: begin
            if (i_valid) begin
                next_shift = {i_data_re, i_data_im};
                next_cnt   = TOTAL_BITS - 1;
                if (current_samp == 0)
                    next_state = STATE_START;
                else
                    next_state = STATE_SEND;
            end
        end
        STATE_START: begin
            data       = 1'b1;
            next_state = STATE_SEND;
        end
        STATE_SEND: begin
            data       = current_shift[TOTAL_BITS-1];
            next_shift = {current_shift[TOTAL_BITS-2:0], 1'b0};
            if (current_cnt == 0) begin
                next_state = STATE_IDLE;
                next_samp  = (current_samp == SAMP_W'(N_DATA - 1))
                             ? 0
                             : current_samp + 1;
            end
            else begin
                next_cnt = current_cnt - 1;
            end
        end
        default: next_state = STATE_IDLE;
    endcase
end

endmodule