`timescale 1ns / 1ps

module uart_config_tb;

    localparam CLK_FREQ   = 160;
    localparam BAUD_RATE  = 10;
    localparam BAUD_DIV   = CLK_FREQ / BAUD_RATE;
    localparam CLK_PERIOD = 10;
    localparam BIT_PERIOD = BAUD_DIV * CLK_PERIOD;

    reg         clk;
    reg         rst_n;
    reg         uart_rx;
    wire [51:0] config_bits;
    wire        config_done;
    wire        config_error;

    integer pass_count = 0;
    integer fail_count = 0;

    uart_config #(
        .CLK_FREQ  (CLK_FREQ),
        .BAUD_RATE (BAUD_RATE)
    ) dut (
        .clk          (clk),
        .rst_n        (rst_n),
        .uart_rx      (uart_rx),
        .config_bits  (config_bits),
        .config_done  (config_done),
        .config_error (config_error)
    );

    initial clk = 0;
    always #(CLK_PERIOD/2) clk = ~clk;

    task wait_clks(input integer n);
        integer i;
        begin
            for (i = 0; i < n; i = i + 1)
                @(posedge clk);
        end
    endtask

    task do_reset;
        begin
            rst_n = 0;
            uart_rx = 1;
            wait_clks(4);
            rst_n = 1;
            wait_clks(2);
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

    task uart_send_bad_stop(input [7:0] data);
        integer i;
        begin
            uart_rx = 0;
            #(BIT_PERIOD);
            for (i = 0; i < 8; i = i + 1) begin
                uart_rx = data[i];
                #(BIT_PERIOD);
            end
            uart_rx = 0;
            #(BIT_PERIOD);
            uart_rx = 1;
            #(BIT_PERIOD);
        end
    endtask

    task check_done(input [15*8-1:0] label, input expected);
        begin
            if (config_done !== expected) begin
                $display("  FAIL: %s | config_done got %b expected %b",
                         label, config_done, expected);
                fail_count = fail_count + 1;
            end else begin
                $display("  PASS: %s | done=%b", label, expected);
                pass_count = pass_count + 1;
            end
        end
    endtask

    task check_error(input [15*8-1:0] label, input expected);
        begin
            if (config_error !== expected) begin
                $display("  FAIL: %s | config_error got %b expected %b",
                         label, config_error, expected);
                fail_count = fail_count + 1;
            end else begin
                $display("  PASS: %s | error=%b", label, expected);
                pass_count = pass_count + 1;
            end
        end
    endtask

    task check_bits(input [15*8-1:0] label, input [51:0] expected);
        begin
            if (config_bits !== expected) begin
                $display("  FAIL: %s | bits got %h expected %h",
                         label, config_bits, expected);
                fail_count = fail_count + 1;
            end else begin
                $display("  PASS: %s | bits=%h", label, expected);
                pass_count = pass_count + 1;
            end
        end
    endtask

    initial begin
        $dumpfile("uart_config_tb.vcd");
        $dumpvars(0, uart_config_tb);

        $display("\n==========================================");
        $display("  UART Config Loader Testbench");
        $display("  BAUD_DIV=%0d  BIT_PERIOD=%0dns",
                 BAUD_DIV, BIT_PERIOD);
        $display("==========================================");

        rst_n   = 0;
        uart_rx = 1;

        do_reset;
        uart_send_config(56'h00_00_00_00_00_00_00);
        wait_clks(4); #1;
        check_bits( "ZERO bits      ", 52'h0_0000_0000_0000);
        check_done( "ZERO done      ", 1'b1);
        check_error("ZERO error     ", 1'b0);

        do_reset;
        uart_send_config(56'h01_23_45_67_89_AB_CD);
        wait_clks(4); #1;
        check_bits( "PAT bits       ", 52'h1_2345_6789_ABCD);
        check_done( "PAT done       ", 1'b1);
        check_error("PAT error      ", 1'b0);

        do_reset;
        uart_send_config(56'h0F_FF_FF_FF_FF_FF_FF);
        wait_clks(4); #1;
        check_bits( "MAX bits       ", 52'hF_FFFF_FFFF_FFFF);
        check_done( "MAX done       ", 1'b1);
        check_error("MAX error      ", 1'b0);

        do_reset;
        uart_send_config(56'h0A_AA_AA_AA_AA_AA_AA);
        wait_clks(4); #1;
        check_bits( "ALT bits       ", 52'hA_AAAA_AAAA_AAAA);
        check_done( "ALT done       ", 1'b1);
        check_error("ALT error      ", 1'b0);

        do_reset;
        uart_send_config(56'h00_00_00_00_00_00_01);
        wait_clks(4); #1;
        check_bits( "LSB bits       ", 52'h0_0000_0000_0001);
        check_done( "LSB done       ", 1'b1);

        do_reset;

        uart_send_byte(8'h00);
        wait_clks(4); #1;
        check_done("AFTER 1 byte   ", 1'b0);

        uart_send_byte(8'hAA);
        uart_send_byte(8'hBB);
        wait_clks(4); #1;
        check_done("AFTER 3 bytes  ", 1'b0);

        uart_send_byte(8'hCC);
        uart_send_byte(8'hDD);
        uart_send_byte(8'hEE);
        wait_clks(4); #1;
        check_done("AFTER 6 bytes  ", 1'b0);

        uart_send_byte(8'hFF);
        wait_clks(4); #1;
        check_done("AFTER 7 bytes  ", 1'b1);
        check_bits("ACCUM value    ", 52'h0_AABB_CCDD_EEFF);

        do_reset;
        uart_send_byte(8'h00);
        uart_send_bad_stop(8'hAA);
        wait_clks(4); #1;
        check_error("BADSTOP err    ", 1'b1);
        check_done( "BADSTOP done   ", 1'b0);

        uart_send_byte(8'hBB);
        uart_send_byte(8'hCC);
        uart_send_byte(8'hDD);
        uart_send_byte(8'hEE);
        uart_send_byte(8'hFF);
        wait_clks(4); #1;
        check_done( "BLOCKED done   ", 1'b0);
        check_error("BLOCKED err    ", 1'b1);

        do_reset;
        uart_rx = 0;
        #(CLK_PERIOD * 4);
        uart_rx = 1;
        #(BIT_PERIOD * 2);
        wait_clks(4); #1;
        check_error("GLITCH err     ", 1'b1);
        check_done( "GLITCH done    ", 1'b0);

        do_reset;
        uart_send_byte(8'hF0);
        wait_clks(4); #1;
        check_error("BAD NIB err    ", 1'b1);

        do_reset;
        uart_send_byte(8'h05);
        wait_clks(4); #1;
        check_error("GOOD NIB err   ", 1'b0);

        do_reset;
        uart_send_config(56'h0F_FF_FF_FF_FF_FF_FF);
        wait_clks(4);
        do_reset;
        wait_clks(2); #1;
        check_done( "RST done       ", 1'b0);
        check_error("RST error      ", 1'b0);
        check_bits( "RST bits       ", 52'h0);

        do_reset;
        uart_send_bad_stop(8'hFF);
        wait_clks(4); #1;
        check_error("PRE-RST err    ", 1'b1);
        do_reset;
        wait_clks(2); #1;
        check_error("POST-RST err   ", 1'b0);

        do_reset;
        uart_send_byte(8'h0D);
        uart_send_byte(8'hEA);
        uart_send_byte(8'hDB);
        rst_n = 0;
        wait_clks(4);
        rst_n = 1;
        wait_clks(2); #1;
        check_done( "MIDRST done    ", 1'b0);
        check_bits( "MIDRST bits    ", 52'h0);
        check_error("MIDRST err     ", 1'b0);

        uart_send_config(56'h05_55_55_55_55_55_55);
        wait_clks(4); #1;
        check_bits( "RECOV bits     ", 52'h5_5555_5555_5555);
        check_done( "RECOV done     ", 1'b1);
        check_error("RECOV error    ", 1'b0);

        do_reset;
        uart_send_config(56'h00_11_22_33_44_55_66);
        wait_clks(4); #1;
        check_done( "PRE-EXT done   ", 1'b1);
        uart_send_byte(8'hFF);
        uart_send_byte(8'hFF);
        uart_send_byte(8'hFF);
        wait_clks(4); #1;
        check_bits( "EXTRA bits     ", 52'h0_1122_3344_5566);
        check_done( "EXTRA done     ", 1'b1);

        wait_clks(100); #1;
        check_done( "LATCH done     ", 1'b1);
        check_bits( "LATCH bits     ", 52'h0_1122_3344_5566);

        do_reset;
        begin : tight_block
            integer b, i;
            reg [55:0] vec;
            vec = 56'h03_14_15_92_65_35_89;
            for (b = 6; b >= 0; b = b - 1) begin
                uart_rx = 0;
                #(BIT_PERIOD);
                for (i = 0; i < 8; i = i + 1) begin
                    uart_rx = vec[b*8 + i];
                    #(BIT_PERIOD);
                end
                uart_rx = 1;
                #(BIT_PERIOD);
            end
        end
        wait_clks(4); #1;
        check_bits( "TIGHT bits     ", 52'h3_1415_9265_3589);
        check_done( "TIGHT done     ", 1'b1);
        check_error("TIGHT error    ", 1'b0);

        #100;
        $display("\n==========================================");
        $display("  RESULTS: %0d PASSED, %0d FAILED", pass_count, fail_count);
        $display("==========================================\n");

        $finish;
    end

endmodule
