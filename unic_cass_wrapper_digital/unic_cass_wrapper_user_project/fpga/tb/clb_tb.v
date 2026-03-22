`timescale 1ns/1ps

module clb_tb;

    reg clk_i;
    reg rst_ni;

    reg from_north;
    reg from_south;
    reg from_east;
    reg from_west;

    reg [1:0] local_inputs;
    reg [12:0] confi;

    wire to_north;
    wire to_south;
    wire to_east;
    wire to_west;
    wire local_output;

    clb uut (
        .clk_i(clk_i),
        .rst_ni(rst_ni),
        .from_north(from_north),
        .from_south(from_south),
        .from_east(from_east),
        .from_west(from_west),
        .local_inputs(local_inputs),
        .confi(confi),
        .to_north(to_north),
        .to_south(to_south),
        .to_east(to_east),
        .to_west(to_west),
        .local_output(local_output)
    );

    initial clk_i = 0;
    always #5 clk_i = ~clk_i;

    initial begin
        $dumpfile("clb_tb.vcd");
        $dumpvars(0, clb_tb);
    end

    initial begin
        rst_ni = 0;

        from_north = 0;
        from_south = 0;
        from_east  = 0;
        from_west  = 0;

        local_inputs = 2'b00;
        confi = 13'd0;

        #20;
        rst_ni = 1;
        #10;

        // TEST 1: AND mode
        $display("=== TEST 1: AND mode ===");
        confi[1:0]   = 2'b00;
        confi[4:2]   = 3'b100;
        confi[7:5]   = 3'b101;
        confi[11:8]  = 4'b0001;
        confi[12]    = 1'b0;

        local_inputs = 2'b00; #10;
        $display("  A=0 B=0 -> local_output=%b to_north=%b (expect 0)", local_output, to_north);
        local_inputs = 2'b01; #10;
        $display("  A=1 B=0 -> local_output=%b to_north=%b (expect 0)", local_output, to_north);
        local_inputs = 2'b10; #10;
        $display("  A=0 B=1 -> local_output=%b to_north=%b (expect 0)", local_output, to_north);
        local_inputs = 2'b11; #10;
        $display("  A=1 B=1 -> local_output=%b to_north=%b (expect 1)", local_output, to_north);

        // TEST 2: OR mode
        $display("=== TEST 2: OR mode ===");
        confi[1:0]   = 2'b01;
        confi[11:8]  = 4'b0010;

        local_inputs = 2'b00; #10;
        $display("  A=0 B=0 -> local_output=%b to_south=%b (expect 0)", local_output, to_south);
        local_inputs = 2'b01; #10;
        $display("  A=1 B=0 -> local_output=%b to_south=%b (expect 1)", local_output, to_south);
        local_inputs = 2'b10; #10;
        $display("  A=0 B=1 -> local_output=%b to_south=%b (expect 1)", local_output, to_south);
        local_inputs = 2'b11; #10;
        $display("  A=1 B=1 -> local_output=%b to_south=%b (expect 1)", local_output, to_south);

        // TEST 3: XOR mode with FF
        $display("=== TEST 3: XOR mode with FF ===");
        confi[1:0]   = 2'b10;
        confi[11:8]  = 4'b0100;
        confi[12]    = 1'b1;

        local_inputs = 2'b00;
        @(posedge clk_i); #1;
        $display("  A=0 B=0 -> local_output=%b to_east=%b (expect 0 after clk)", local_output, to_east);

        local_inputs = 2'b01;
        @(posedge clk_i); #1;
        $display("  A=1 B=0 -> local_output=%b to_east=%b (expect 1 after clk)", local_output, to_east);

        local_inputs = 2'b10;
        @(posedge clk_i); #1;
        $display("  A=0 B=1 -> local_output=%b to_east=%b (expect 1 after clk)", local_output, to_east);

        local_inputs = 2'b11;
        @(posedge clk_i); #1;
        $display("  A=1 B=1 -> local_output=%b to_east=%b (expect 0 after clk)", local_output, to_east);

        // TEST 4: Pass-through B
        $display("=== TEST 4: Mode 11 (pass-through B) ===");
        confi[1:0]   = 2'b11;
        confi[4:2]   = 3'b000;
        confi[7:5]   = 3'b011;
        confi[11:8]  = 4'b1000;
        confi[12]    = 1'b0;

        from_north = 0; from_west = 0; #10;
        $display("  A=0 B=0 -> local_output=%b to_west=%b (expect 0)", local_output, to_west);
        from_north = 0; from_west = 1; #10;
        $display("  A=0 B=1 -> local_output=%b to_west=%b (expect 1)", local_output, to_west);
        from_north = 1; from_west = 0; #10;
        $display("  A=1 B=0 -> local_output=%b to_west=%b (expect 0)", local_output, to_west);
        from_north = 1; from_west = 1; #10;
        $display("  A=1 B=1 -> local_output=%b to_west=%b (expect 1)", local_output, to_west);

        // TEST 5: Reset with FF
        $display("=== TEST 5: Reset with FF ===");
        confi[1:0]   = 2'b01;
        confi[4:2]   = 3'b100;
        confi[7:5]   = 3'b101;
        confi[11:8]  = 4'b0001;
        confi[12]    = 1'b1;

        local_inputs = 2'b11;
        @(posedge clk_i); #1;
        $display("  Before reset: local_output=%b (expect 1)", local_output);

        rst_ni = 0; #20;
        $display("  During reset: local_output=%b (expect 0)", local_output);

        rst_ni = 1;
        @(posedge clk_i); #1;
        $display("  After reset, 1 clk: local_output=%b (expect 1)", local_output);

        // TEST 6: Routing check
        $display("=== TEST 6: Routing check ===");
        confi[1:0]   = 2'b01;
        confi[4:2]   = 3'b100;
        confi[7:5]   = 3'b101;
        confi[11:8]  = 4'b0101;
        confi[12]    = 1'b0;

        local_inputs = 2'b11; #10;
        $display("  Route=0101: N=%b S=%b E=%b W=%b local=%b (expect 1,0,1,0,1)",
                 to_north, to_south, to_east, to_west, local_output);

        #50;
        $display("=== ALL TESTS COMPLETE ===");
        $finish;
    end

endmodule
