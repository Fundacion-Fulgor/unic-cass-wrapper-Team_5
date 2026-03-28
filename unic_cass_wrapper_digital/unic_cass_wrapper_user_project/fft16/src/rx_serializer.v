module rx_serializer #(
    parameter NB_DATA = 8,
    parameter N_DATA  = 16
)(
    `ifdef USE_POWER_PINS
    inout                           VPWR,
    inout                           VGND,
    `endif
    input                           i_clk,
    input                           i_rst_n,
    input                           i_data,
    output reg signed [NB_DATA-1:0] o_data_re,
    output reg signed [NB_DATA-1:0] o_data_im,
    output reg                      o_valid
);

localparam TOTAL_BITS = 2 * NB_DATA;
localparam NB_CNT     = 5;
localparam SAMP_W     = $clog2(N_DATA);

localparam STATE_IDLE = 1'b0;
localparam STATE_RECV = 1'b1;

reg                  current_state, next_state;
reg [NB_CNT-1:0]      current_cnt,   next_cnt;
reg [TOTAL_BITS-1:0] current_shift, next_shift;
reg [SAMP_W-1:0]     current_samp,  next_samp;

reg  data_d;
wire start_detected;

always @(posedge i_clk or negedge i_rst_n) begin
    if (!i_rst_n) data_d <= 1'b0;
    else          data_d <= i_data;
end

assign start_detected = (i_data && !data_d);

always @(posedge i_clk or negedge i_rst_n) begin
    if (!i_rst_n) begin
        current_state <= STATE_IDLE;
        current_cnt   <= 0;
        current_shift <= 0;
        current_samp  <= 0;
        o_valid       <= 1'b0;
        o_data_re     <= 0;
        o_data_im     <= 0;
    end
    else begin
        current_state <= next_state;
        current_cnt   <= next_cnt;
        current_shift <= next_shift;
        current_samp  <= next_samp;
        if (current_state == STATE_RECV && current_cnt == TOTAL_BITS - 1) begin
            o_data_re <= next_shift[TOTAL_BITS-1 -: NB_DATA];
            o_data_im <= next_shift[NB_DATA-1    -: NB_DATA];
            o_valid   <= 1'b1;
        end
        else begin
            o_valid   <= 1'b0;
        end
    end
end

always @(*) begin
    next_state = current_state;
    next_cnt   = current_cnt;
    next_shift = {current_shift[TOTAL_BITS-2:0], i_data};
    next_samp  = current_samp;

    case (current_state)
        STATE_IDLE: begin
            next_cnt  = 0;
            next_samp = 0;
            if (start_detected) begin
                next_state = STATE_RECV;
            end
        end

        STATE_RECV: begin
            if (current_cnt == TOTAL_BITS - 1) begin
                next_cnt = 0;
                if ({ {(32-SAMP_W){1'b0}}, current_samp } == (N_DATA - 1)) begin
                    next_state = STATE_IDLE;
                end
                else begin
                    next_samp = current_samp + 1;
                end
            end
            else begin
                next_cnt = current_cnt + 1;
            end
        end

        default: next_state = STATE_IDLE;
    endcase
end

endmodule
