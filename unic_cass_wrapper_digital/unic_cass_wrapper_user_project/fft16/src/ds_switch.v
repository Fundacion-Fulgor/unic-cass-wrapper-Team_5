//=============================================================================
// Updated: 2026-09-01
// Delay commutator for the MDC pipeline. Collects two consecutive input pairs
// into four words and reads them back out re-paired, so that samples that
// arrived in different cycles are presented side by side.
//=============================================================================

module ds_switch #(
    parameter NB = 8
) (
    `ifdef USE_POWER_PINS
    inout             VPWR,
    inout             VGND,
    `endif
    output            o_valid,
    output [NB-1 : 0] o_data_0r,
    output [NB-1 : 0] o_data_0i,
    output [NB-1 : 0] o_data_1r,
    output [NB-1 : 0] o_data_1i,
    input             i_clk,
    input             i_rstn,
    input             i_valid,
    input  [NB-1 : 0] i_data_0r,
    input  [NB-1 : 0] i_data_0i,
    input  [NB-1 : 0] i_data_1r,
    input  [NB-1 : 0] i_data_1i
);

reg  [NB-1:0] mem_0r;
reg  [NB-1:0] mem_0i;
reg  [NB-1:0] mem_1r;
reg  [NB-1:0] mem_1i;
reg  [NB-1:0] mem_2r;
reg  [NB-1:0] mem_2i;
reg  [NB-1:0] mem_3r;
reg  [NB-1:0] mem_3i;

reg  [NB-1:0] data_0r_d;
reg  [NB-1:0] data_0i_d;
reg  [NB-1:0] data_1r_d;
reg  [NB-1:0] data_1i_d;

reg           valid_d;
reg           wr_phase;
reg           rd_phase;
reg           transmitting;

wire          wr_done;
wire          rd_done;

assign wr_done = i_valid && wr_phase;
assign rd_done = transmitting && rd_phase;

always @(posedge i_clk) begin
    if (!i_rstn) begin
        wr_phase     <= 1'b0;
        rd_phase     <= 1'b0;
        transmitting <= 1'b0;
        valid_d      <= 1'b0;
    end
    else begin
        if (i_valid) begin
            if (wr_phase == 1'b0) begin
                mem_0r <= i_data_0r;
                mem_0i <= i_data_0i;
                mem_2r <= i_data_1r;
                mem_2i <= i_data_1i;
            end
            else begin
                mem_1r <= i_data_0r;
                mem_1i <= i_data_0i;
                mem_3r <= i_data_1r;
                mem_3i <= i_data_1i;
            end
            wr_phase <= ~wr_phase;
        end

        if (transmitting) begin
            if (rd_phase == 1'b0) begin
                data_0r_d <= mem_0r;
                data_0i_d <= mem_0i;
                data_1r_d <= mem_1r;
                data_1i_d <= mem_1i;
            end
            else begin
                data_0r_d <= mem_2r;
                data_0i_d <= mem_2i;
                data_1r_d <= mem_3r;
                data_1i_d <= mem_3i;
            end
            rd_phase <= ~rd_phase;
        end

        valid_d      <= transmitting;
        transmitting <= wr_done ? 1'b1 : (rd_done ? 1'b0 : transmitting);
    end
end

assign o_data_0r = data_0r_d;
assign o_data_0i = data_0i_d;
assign o_data_1r = data_1r_d;
assign o_data_1i = data_1i_d;
assign o_valid   = valid_d;

endmodule
