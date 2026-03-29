`timescale 1ns / 1ps

module fpga(
    `ifdef USE_POWER_PINS
    inout VPWR,
    inout VGND,
    `endif
    input  wire clk_i,
    input  wire rst_ni,
    input  wire [6:4] ui_PAD2CORE,
    output wire [2:2] uo_CORE2PAD
);

    parameter CLK_FREQ  = 100_000_000;
    parameter BAUD_RATE = 9600;

    reg [16:0] ui_reg;
    always @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni)
            ui_reg <= 17'b0;
        else
            ui_reg <= ui_PAD2CORE;
    end

    wire uart_rx = ui_reg[0];
    wire [1:0] user_inputs = ui_reg[2:1];

    wire [51:0] config_bits;
    wire        config_done;
    wire        config_error;
    wire        fabric_out;

    uart_config #(
        .CLK_FREQ  (CLK_FREQ),
        .BAUD_RATE (BAUD_RATE)
    ) uart_inst (
        .clk          (clk_i),
        .rst_n        (rst_ni),
        .uart_rx      (uart_rx),
        .config_bits  (config_bits),
        .config_done  (config_done),
        .config_error (config_error)
    );

    fabric_2x2 fabric_inst (
        .clk          (clk_i),
        .rst_n        (rst_ni),
        .config_bits  (config_bits),
        .user_inputs  (user_inputs),
        .user_output  (fabric_out)
    );

    reg [16:0] uo_reg;
    always @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni)
            uo_reg <= 17'b0;
        else begin
            uo_reg[0]    <= config_done & fabric_out;
            uo_reg[16:1] <= 16'b0;
        end
    end

    assign uo_CORE2PAD = uo_reg;

endmodule
