`timescale 1ns/1ps

module tb_top_DCO;

    reg  clk_i;
    reg  rst_ni;
    reg  [16:0] ui_PAD2CORE;
    wire [16:0] uo_CORE2PAD;
    reg [31:0] cur_trim; 
    integer i;

    user_project dut (
        .clk_i(clk_i),
        .rst_ni(rst_ni),
        .ui_PAD2CORE(ui_PAD2CORE),
        .uo_CORE2PAD(uo_CORE2PAD)
    );

    initial begin
        ui_PAD2CORE[0] = 1'b0; 
        forever #50 ui_PAD2CORE[0] = ~ui_PAD2CORE[0];
    end

    task spi_write(input [7:0] addr, input [31:0] data);
       integer k;
        begin
            ui_PAD2CORE[2] = 0; // CS_N Low
            #200;
            for (k = 7; k >= 0; k = k - 1) begin
                ui_PAD2CORE[3] = addr[k];
                #100 ui_PAD2CORE[1] = 1; #100 ui_PAD2CORE[1] = 0;
            end
            for (k = 31; k >= 0; k = k - 1) begin
                ui_PAD2CORE[3] = data[k];
                #100 ui_PAD2CORE[1] = 1; #100 ui_PAD2CORE[1] = 0;
            end

            #100 ui_PAD2CORE[1] = 1; #100 ui_PAD2CORE[1] = 0;
            #100 ui_PAD2CORE[2] = 1;
            #500;
        end
    endtask

    task measure_clock_period(input [31:0] trim );
        real t1, t2, period;
        begin
            @(posedge uo_CORE2PAD[1]); 
            t1 = $realtime;
            
            @(posedge uo_CORE2PAD[1]); 
            t2 = $realtime;
            
            period = t2 - t1;
           
            $display("[%t]|%h |Period = %0.3f ns | Freq = %0.3f MHz",$time,trim,period, 1000.0/period);
        end
    endtask
    initial begin 
	rst_ni = 0;
	ui_PAD2CORE[1] = 0; 
	ui_PAD2CORE[2] = 1; 
	ui_PAD2CORE[3] = 0;
        cur_trim = 32'b0;
        #500 rst_ni = 1;

        $display("[%t] Configuring DCO Mode...", $time);
        spi_write(8'h00, 32'h00000003);
	$display("write complete");
	#2000;
        $display("-------------------------------------------------------------");
	$display("Time          | Ext_Trim Value | Measured Output Clock");
	$display("-------------------------------------------------------------");
	measure_clock_period(cur_trim);
       for (i = 0; i < 26; i = i + 1) begin	
	    cur_trim[i] = 1;
	    cur_trim[26] = 1;
            spi_write(8'h01,cur_trim);
            #2000; 
            measure_clock_period(cur_trim); 
        end

        $display("-------------------------------------------------------------");
        $finish;
    end
    
    
/*    initial begin
        $dumpfile("wave.vcd");
        $dumpvars(0, tb_top_DCO);
    end
initial begin
    #10000000;
    
    $display("Error: Timeout! Simulation ran too long.");
    $finish;
end*/
endmodule
