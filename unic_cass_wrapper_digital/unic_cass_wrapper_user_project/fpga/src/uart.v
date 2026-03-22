`timescale 1ns / 1ps

module uart_config #(
    parameter CLK_FREQ  = 100_000_000,
    parameter BAUD_RATE = 9600
)(
    input  wire        clk,
    input  wire        rst_n,
    input  wire        uart_rx,

    output reg  [51:0] config_bits,
    output reg         config_done,
    output wire        config_error
);

    localparam BAUD_DIV   = CLK_FREQ / BAUD_RATE;
    localparam HALF_BIT   = BAUD_DIV / 2;
    localparam NUM_BYTES  = 7;
    localparam BAUD_CNT_W = $clog2(BAUD_DIV + 1);

    reg uart_rx_sync1, uart_rx_sync2;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            uart_rx_sync1 <= 1'b1;
            uart_rx_sync2 <= 1'b1;
        end else begin
            uart_rx_sync1 <= uart_rx;
            uart_rx_sync2 <= uart_rx_sync1;
        end
    end
    wire uart_rx_clean = uart_rx_sync2;

    reg framing_error;
    reg nibble_error;

    assign config_error = framing_error | nibble_error;

    localparam [2:0] IDLE  = 3'd0,
                     START = 3'd1,
                     DATA  = 3'd2,
                     STOP  = 3'd3;

    reg [2:0]              rx_state;
    reg [BAUD_CNT_W-1:0]   baud_counter;
    reg [2:0]              bit_index;
    reg [7:0]              rx_byte;
    reg                    rx_done;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rx_state      <= IDLE;
            baud_counter  <= 0;
            bit_index     <= 0;
            rx_byte       <= 8'd0;
            rx_done       <= 1'b0;
            framing_error <= 1'b0;
        end else begin
            rx_done <= 1'b0;

            case (rx_state)

                IDLE: begin
                    baud_counter <= 0;
                    bit_index    <= 0;
                    if (!uart_rx_clean)
                        rx_state <= START;
                end

                START: begin
                    if (baud_counter == HALF_BIT - 1) begin
                        if (!uart_rx_clean) begin
                            baud_counter <= 0;
                            rx_state     <= DATA;
                        end else begin
                            rx_state      <= IDLE;
                            framing_error <= 1'b1;
                        end
                    end else
                        baud_counter <= baud_counter + 1;
                end

                DATA: begin
                    if (baud_counter == BAUD_DIV - 1) begin
                        baud_counter       <= 0;
                        rx_byte[bit_index] <= uart_rx_clean;
                        if (bit_index == 3'd7) begin
                            bit_index <= 0;
                            rx_state  <= STOP;
                        end else
                            bit_index <= bit_index + 1;
                    end else
                        baud_counter <= baud_counter + 1;
                end

                STOP: begin
                    if (baud_counter == BAUD_DIV - 1) begin
                        baud_counter <= 0;
                        if (uart_rx_clean) begin
                            rx_done  <= 1'b1;
                            rx_state <= IDLE;
                        end else begin
                            rx_state      <= IDLE;
                            framing_error <= 1'b1;
                        end
                    end else
                        baud_counter <= baud_counter + 1;
                end

                default: rx_state <= IDLE;

            endcase
        end
    end

    reg [51:0] config_shift;
    reg [2:0]  byte_count;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            config_shift <= 52'd0;
            config_bits  <= 52'd0;
            config_done  <= 1'b0;
            byte_count   <= 3'd0;
            nibble_error <= 1'b0;
        end else begin
            if (rx_done && !config_done && !config_error) begin
                config_shift <= {config_shift[43:0], rx_byte};
                byte_count   <= byte_count + 1;

                if (byte_count == 3'd0 && rx_byte[7:4] != 4'b0000)
                    nibble_error <= 1'b1;

                if (byte_count == NUM_BYTES - 1) begin
                    config_bits <= {config_shift[43:0], rx_byte};
                    config_done <= 1'b1;
                end
            end
        end
    end

endmodule
