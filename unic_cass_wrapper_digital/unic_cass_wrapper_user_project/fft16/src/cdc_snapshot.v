//=============================================================================
// Updated: 2026-09-01
// Freezes a bus from the system clock domain so it can be read out safely by
// a slower asynchronous interface. The trigger is synchronised with three
// flops and its falling edge captures the current input value.
//=============================================================================

module cdc_snapshot #(
    parameter DATA_WIDTH = 8
) (
    `ifdef USE_POWER_PINS
    inout                        VPWR,
    inout                        VGND,
    `endif
    output reg  [DATA_WIDTH-1:0] o_data,
    input                        i_clk,
    input                        i_rstn,
    input                        i_trigger_n,
    input       [DATA_WIDTH-1:0] i_data
);

reg  trig_d;
reg  trig_2d;
reg  trig_3d;
wire capture;

always @(posedge i_clk) begin
    if (!i_rstn) begin
        trig_d  <= 1'b1;
        trig_2d <= 1'b1;
        trig_3d <= 1'b1;
    end
    else begin
        trig_d  <= i_trigger_n;
        trig_2d <= trig_d;
        trig_3d <= trig_2d;
    end
end

assign capture = trig_3d && !trig_2d;

always @(posedge i_clk) begin
    if (!i_rstn) begin
        o_data <= {DATA_WIDTH{1'b0}};
    end
    else if (capture) begin
        o_data <= i_data;
    end
end

endmodule
