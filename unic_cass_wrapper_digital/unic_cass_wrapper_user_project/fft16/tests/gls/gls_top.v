//=============================================================================
// Updated: 2026-09-06
// Verification-only wrapper for gate level simulation. Presents the synthesised
// fft16_project netlist under the same port names as the RTL top_fft16, so the
// bring-up testbench runs unchanged against the netlist.
//=============================================================================

module gls_top (
    output wire o_data,
    output wire o_spi_miso,
    input  wire i_clk,
    input  wire i_rstn,
    input  wire i_data,
    input  wire i_spi_ss_n,
    input  wire i_spi_sclk,
    input  wire i_spi_mosi
);

wire [3:0] pad2core;
wire [1:0] core2pad;

assign pad2core   = {i_spi_mosi, i_spi_sclk, i_spi_ss_n, i_data};
assign o_data     = core2pad[0];
assign o_spi_miso = core2pad[1];

fft16_project u_fft16_project (
    .clk_i       (i_clk),
    .rst_ni      (i_rstn),
    .ui_PAD2CORE (pad2core),
    .uo_CORE2PAD (core2pad)
);

endmodule
