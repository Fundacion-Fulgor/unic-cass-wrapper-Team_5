`timescale 1ns/1ps

module fabric_2x2_tb;

    reg         clk;
    reg         rst_n;
    reg  [51:0] config_bits;
    reg  [1:0]  user_inputs;
    wire        user_output;

    fabric_2x2 uut (
        .clk(clk),
        .rst_n(rst_n),
        .config_bits(config_bits),
        .user_inputs(user_inputs),
        .user_output(user_output)
    );

    initial clk = 0;
    always #5 clk = ~clk;

    initial begin
        $dumpfile("fabric_2x2_tb.vcd");
        $dumpvars(0, fabric_2x2_tb);
    end

    initial begin
        #10000;
        $display("\n[TIMEOUT] Simulation exceeded 10us - forcing finish");
        $finish;
    end

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

    task wait_clks;
        input integer n;
        integer i;
    begin
        for (i = 0; i < n; i = i + 1)
            @(posedge clk);
    end
    endtask

    integer pass_count;
    integer fail_count;

    task check;
        input [119:0] test_name;
        input         expected;
    begin
        #1;
        if (user_output === expected) begin
            $display("  [PASS] %s : user_output=%b (expected %b)", test_name, user_output, expected);
            pass_count = pass_count + 1;
        end else begin
            $display("  [FAIL] %s : user_output=%b (expected %b)", test_name, user_output, expected);
            fail_count = fail_count + 1;
        end
    end
    endtask

    initial begin
        pass_count = 0;
        fail_count = 0;

        rst_n       = 0;
        config_bits = 52'd0;
        user_inputs = 2'b00;

        #25;
        rst_n = 1;
        #10;

        $display("\n=== TEST 1: Single-bit pass-through (3 CLBs) ===");

        config_bits[12:0]   = make_config(2'b11, 3'd0, 3'd4, 4'b0100, 1'b0);
        config_bits[25:13]  = make_config(2'b11, 3'd0, 3'd3, 4'b0010, 1'b0);
        config_bits[38:26]  = 13'd0;
        config_bits[51:39]  = make_config(2'b11, 3'd0, 3'd0, 4'b0000, 1'b0);

        user_inputs = 2'b00; #10;
        check("UI0=0          ", 1'b0);

        user_inputs = 2'b01; #10;
        check("UI0=1          ", 1'b1);

        user_inputs = 2'b00; #10;
        check("UI0=0 rev      ", 1'b0);

        $display("\n=== TEST 2: AND gate through fabric ===");

        config_bits[12:0]   = make_config(2'b00, 3'd4, 3'd5, 4'b0100, 1'b0);
        config_bits[25:13]  = make_config(2'b11, 3'd0, 3'd3, 4'b0010, 1'b0);
        config_bits[38:26]  = 13'd0;
        config_bits[51:39]  = make_config(2'b11, 3'd0, 3'd0, 4'b0000, 1'b0);

        user_inputs = 2'b00; #10;
        check("AND 00         ", 1'b0);

        user_inputs = 2'b01; #10;
        check("AND 01         ", 1'b0);

        user_inputs = 2'b10; #10;
        check("AND 10         ", 1'b0);

        user_inputs = 2'b11; #10;
        check("AND 11         ", 1'b1);

        $display("\n=== TEST 3: OR gate through fabric ===");

        config_bits[12:0]   = make_config(2'b01, 3'd4, 3'd5, 4'b0100, 1'b0);
        config_bits[25:13]  = make_config(2'b11, 3'd0, 3'd3, 4'b0010, 1'b0);
        config_bits[38:26]  = 13'd0;
        config_bits[51:39]  = make_config(2'b11, 3'd0, 3'd0, 4'b0000, 1'b0);

        user_inputs = 2'b00; #10;
        check("OR 00          ", 1'b0);

        user_inputs = 2'b01; #10;
        check("OR 01          ", 1'b1);

        user_inputs = 2'b10; #10;
        check("OR 10          ", 1'b1);

        user_inputs = 2'b11; #10;
        check("OR 11          ", 1'b1);

        $display("\n=== TEST 4: XOR with flip-flop ===");

        config_bits[12:0]   = make_config(2'b10, 3'd4, 3'd5, 4'b0100, 1'b1);
        config_bits[25:13]  = make_config(2'b11, 3'd0, 3'd3, 4'b0010, 1'b0);
        config_bits[38:26]  = 13'd0;
        config_bits[51:39]  = make_config(2'b11, 3'd0, 3'd0, 4'b0000, 1'b0);

        user_inputs = 2'b00;
        @(posedge clk); #1;
        check("XOR 00 FF      ", 1'b0);

        user_inputs = 2'b01;
        @(posedge clk); #1;
        check("XOR 01 FF      ", 1'b1);

        user_inputs = 2'b10;
        @(posedge clk); #1;
        check("XOR 10 FF      ", 1'b1);

        user_inputs = 2'b11;
        @(posedge clk); #1;
        check("XOR 11 FF      ", 1'b0);

        $display("\n=== TEST 5: Two-level logic (AND then OR) ===");

        config_bits[12:0]   = make_config(2'b00, 3'd4, 3'd5, 4'b0100, 1'b0);
        config_bits[25:13]  = make_config(2'b01, 3'd3, 3'd4, 4'b0010, 1'b0);
        config_bits[38:26]  = 13'd0;
        config_bits[51:39]  = make_config(2'b11, 3'd0, 3'd0, 4'b0000, 1'b0);

        user_inputs = 2'b00; #10;
        check("2LVL 00        ", 1'b0);

        user_inputs = 2'b01; #10;
        check("2LVL 01        ", 1'b1);

        user_inputs = 2'b10; #10;
        check("2LVL 10        ", 1'b0);

        user_inputs = 2'b11; #10;
        check("2LVL 11        ", 1'b1);

        $display("\n=== TEST 6: Vertical routing path ===");

        config_bits[12:0]   = make_config(2'b10, 3'd4, 3'd5, 4'b0010, 1'b0);
        config_bits[25:13]  = 13'd0;
        config_bits[38:26]  = make_config(2'b11, 3'd0, 3'd0, 4'b0100, 1'b0);
        config_bits[51:39]  = make_config(2'b11, 3'd0, 3'd3, 4'b0000, 1'b0);

        user_inputs = 2'b00; #10;
        check("VERT 00        ", 1'b0);

        user_inputs = 2'b01; #10;
        check("VERT 01        ", 1'b1);

        user_inputs = 2'b10; #10;
        check("VERT 10        ", 1'b1);

        user_inputs = 2'b11; #10;
        check("VERT 11        ", 1'b0);

        $display("\n=== TEST 7: All four CLBs active ===");

        config_bits[12:0]   = make_config(2'b00, 3'd4, 3'd5, 4'b0110, 1'b0);
        config_bits[25:13]  = make_config(2'b11, 3'd0, 3'd3, 4'b0010, 1'b0);
        config_bits[38:26]  = make_config(2'b11, 3'd0, 3'd0, 4'b0100, 1'b0);
        config_bits[51:39]  = make_config(2'b10, 3'd0, 3'd3, 4'b0000, 1'b0);

        user_inputs = 2'b00; #10;
        check("ALL4 00        ", 1'b0);

        user_inputs = 2'b01; #10;
        check("ALL4 01        ", 1'b0);

        user_inputs = 2'b10; #10;
        check("ALL4 10        ", 1'b0);

        user_inputs = 2'b11; #10;
        check("ALL4 11        ", 1'b0);

        $display("\n=== TEST 8: Global reset test ===");

        config_bits[12:0]   = make_config(2'b01, 3'd4, 3'd5, 4'b0100, 1'b1);
        config_bits[25:13]  = make_config(2'b11, 3'd0, 3'd3, 4'b0010, 1'b1);
        config_bits[38:26]  = 13'd0;
        config_bits[51:39]  = make_config(2'b11, 3'd0, 3'd0, 4'b0000, 1'b1);

        user_inputs = 2'b11;
        wait_clks(4);
        #1;
        $display("  Before reset: user_output=%b (expect 1)", user_output);

        rst_n = 0;
        #20;
        check("RST active     ", 1'b0);

        rst_n = 1;
        user_inputs = 2'b11;
        wait_clks(4);
        #1;
        check("RST recovery   ", 1'b1);

        $display("\n=== TEST 9: Registered feedback path ===");

        rst_n = 0;
        config_bits[12:0]   = make_config(2'b01, 3'd4, 3'd1, 4'b0110, 1'b1);
        config_bits[25:13]  = make_config(2'b11, 3'd0, 3'd3, 4'b0010, 1'b0);
        config_bits[38:26]  = make_config(2'b11, 3'd0, 3'd0, 4'b0001, 1'b0);
        config_bits[51:39]  = make_config(2'b11, 3'd0, 3'd0, 4'b0000, 1'b0);
        user_inputs = 2'b00;
        #20;

        rst_n = 1;

        @(posedge clk); #1;
        check("FB init 0      ", 1'b0);

        user_inputs = 2'b00;
        @(posedge clk); #1;
        check("FB hold 0      ", 1'b0);

        user_inputs = 2'b01;
        @(posedge clk); #1;
        check("FB set 1       ", 1'b1);

        user_inputs = 2'b00;
        @(posedge clk); #1;
        check("FB held 1      ", 1'b1);

        user_inputs = 2'b00;
        @(posedge clk); #1;
        check("FB still 1     ", 1'b1);

        rst_n = 0; #20;
        rst_n = 1;
        user_inputs = 2'b00;
        @(posedge clk); #1;
        check("FB after rst   ", 1'b0);

        $display("\n=== TEST 10: Mixed operations across CLBs ===");

        config_bits[12:0]   = make_config(2'b10, 3'd4, 3'd5, 4'b0100, 1'b0);
        config_bits[25:13]  = make_config(2'b00, 3'd3, 3'd5, 4'b0010, 1'b0);
        config_bits[38:26]  = 13'd0;
        config_bits[51:39]  = make_config(2'b11, 3'd0, 3'd0, 4'b0000, 1'b0);

        user_inputs = 2'b00; #10;
        check("MIX 00         ", 1'b0);

        user_inputs = 2'b01; #10;
        check("MIX 01         ", 1'b0);

        user_inputs = 2'b10; #10;
        check("MIX 10         ", 1'b1);

        user_inputs = 2'b11; #10;
        check("MIX 11         ", 1'b0);

        #20;
        $display("\n==========================================");
        $display("  RESULTS: %0d PASSED, %0d FAILED", pass_count, fail_count);
        $display("==========================================\n");

        $finish;
    end

endmodule
