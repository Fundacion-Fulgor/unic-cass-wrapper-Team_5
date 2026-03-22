`timescale 1ns / 1ps

module fpga_top_tb;

    localparam CLK_FREQ   = 160;
    localparam BAUD_RATE  = 10;
    localparam BAUD_DIV   = CLK_FREQ / BAUD_RATE;
    localparam CLK_PERIOD = 10;
    localparam BIT_PERIOD = BAUD_DIV * CLK_PERIOD;

    reg        clk;
    reg        rst_n;
    reg        uart_rx;
    reg [1:0]  user_inputs;
    wire       user_output;

    integer pass_count = 0;
    integer fail_count = 0;

    fpga_top #(
        .CLK_FREQ  (CLK_FREQ),
        .BAUD_RATE (BAUD_RATE)
    ) dut (
        .clk         (clk),
        .rst_n       (rst_n),
        .uart_rx     (uart_rx),
        .user_inputs (user_inputs),
        .user_output (user_output)
    );

    initial clk = 0;
    always #(CLK_PERIOD/2) clk = ~clk;

    initial begin
        $dumpfile("fpga_top_tb.vcd");
        $dumpvars(0, fpga_top_tb);
    end

    initial begin
        #10_000_000;
        $display("TIMEOUT!");
        $finish;
    end

    task wait_clks(input integer n);
        integer i;
        begin
            for (i = 0; i < n; i = i + 1)
                @(posedge clk);
        end
    endtask

    task do_reset;
        begin
            rst_n       = 0;
            uart_rx     = 1;
            user_inputs = 2'b00;
            wait_clks(4);
            rst_n = 1;
            wait_clks(2);
        end
    endtask

    task check(input [15*8-1:0] label, input expected);
        begin
            if (user_output !== expected) begin
                $display("  FAIL: %s | got %b expected %b",
                         label, user_output, expected);
                fail_count = fail_count + 1;
            end else begin
                $display("  PASS: %s | out=%b", label, expected);
                pass_count = pass_count + 1;
            end
        end
    endtask

    task uart_send_byte(input [7:0] data);
        integer i;
        begin
            uart_rx = 0;
            #(BIT_PERIOD);
            for (i = 0; i < 8; i = i + 1) begin
                uart_rx = data[i];
                #(BIT_PERIOD);
            end
            uart_rx = 1;
            #(BIT_PERIOD);
            #(BIT_PERIOD);
        end
    endtask

    task uart_send_config(input [55:0] vec);
        integer b;
        begin
            for (b = 6; b >= 0; b = b - 1)
                uart_send_byte(vec[b*8 +: 8]);
        end
    endtask

    function [12:0] make_config;
        input [1:0] mode;
        input [2:0] a_sel;
        input [2:0] b_sel;
        input [3:0] route;
        input       use_ff;
        begin
            make_config = {use_ff, route, b_sel, a_sel, mode};
        end
    endfunction

    reg [12:0] cfg_00, cfg_01, cfg_10, cfg_11;
    reg [55:0] uart_data;

    initial begin
        $display("\n==========================================");
        $display("  FPGA Top Integration Testbench");
        $display("  BAUD_DIV=%0d  BIT_PERIOD=%0dns",
                 BAUD_DIV, BIT_PERIOD);
        $display("==========================================");

        rst_n       = 0;
        uart_rx     = 1;
        user_inputs = 2'b00;

        do_reset;

        cfg_00    = make_config(2'b00, 3'd4, 3'd5, 4'b0010, 1'b0);
        cfg_01    = 13'd0;
        cfg_10    = make_config(2'b11, 3'd0, 3'd0, 4'b0100, 1'b0);
        cfg_11    = make_config(2'b11, 3'd0, 3'd3, 4'b0000, 1'b0);
        uart_data = {4'b0000, cfg_11, cfg_10, cfg_01, cfg_00};

        uart_send_config(uart_data);
        wait_clks(4); #1;

        user_inputs = 2'b00; #10;
        check("AND 00         ", 1'b0);

        user_inputs = 2'b01; #10;
        check("AND 01         ", 1'b0);

        user_inputs = 2'b10; #10;
        check("AND 10         ", 1'b0);

        user_inputs = 2'b11; #10;
        check("AND 11         ", 1'b1);

        do_reset;

        cfg_00    = make_config(2'b01, 3'd4, 3'd5, 4'b0010, 1'b0);
        cfg_01    = 13'd0;
        cfg_10    = make_config(2'b11, 3'd0, 3'd0, 4'b0100, 1'b0);
        cfg_11    = make_config(2'b11, 3'd0, 3'd3, 4'b0000, 1'b0);
        uart_data = {4'b0000, cfg_11, cfg_10, cfg_01, cfg_00};

        uart_send_config(uart_data);
        wait_clks(4); #1;

        user_inputs = 2'b00; #10;
        check("OR 00          ", 1'b0);

        user_inputs = 2'b01; #10;
        check("OR 01          ", 1'b1);

        user_inputs = 2'b10; #10;
        check("OR 10          ", 1'b1);

        user_inputs = 2'b11; #10;
        check("OR 11          ", 1'b1);

        do_reset;

        cfg_00    = make_config(2'b10, 3'd4, 3'd5, 4'b0010, 1'b0);
        cfg_01    = 13'd0;
        cfg_10    = make_config(2'b11, 3'd0, 3'd0, 4'b0100, 1'b0);
        cfg_11    = make_config(2'b11, 3'd0, 3'd3, 4'b0000, 1'b0);
        uart_data = {4'b0000, cfg_11, cfg_10, cfg_01, cfg_00};

        uart_send_config(uart_data);
        wait_clks(4); #1;

        user_inputs = 2'b00; #10;
        check("XOR 00         ", 1'b0);

        user_inputs = 2'b01; #10;
        check("XOR 01         ", 1'b1);

        user_inputs = 2'b10; #10;
        check("XOR 10         ", 1'b1);

        user_inputs = 2'b11; #10;
        check("XOR 11         ", 1'b0);

        #100;
        $display("\n==========================================");
        $display("  RESULTS: %0d PASSED, %0d FAILED",
                 pass_count, fail_count);
        $display("==========================================");

        $finish;
    end

endmodule
