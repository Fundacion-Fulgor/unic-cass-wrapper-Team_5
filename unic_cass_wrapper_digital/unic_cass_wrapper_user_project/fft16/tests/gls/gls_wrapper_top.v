//=============================================================================
// Updated: 2026-09-07
// Verification-only wrapper for gate level simulation of the full chip. Drives
// the synthesised user_project_wrapper_2x2 through its pads and presents the
// four FFT pins under the RTL top_fft16 names, so the bring-up testbench runs
// unchanged from outside the pad ring.
//=============================================================================

module gls_wrapper_top (
    output wire o_data,
    output wire o_spi_miso,
    input  wire i_clk,
    input  wire i_rstn,
    input  wire i_data,
    input  wire i_spi_ss_n,
    input  wire i_spi_sclk,
    input  wire i_spi_mosi
);

localparam UNUSED_UI = 13;

wire [16:0] ui_pad;
wire [16:0] uo_pad;

assign ui_pad = {{UNUSED_UI{1'b0}}, i_spi_mosi, i_spi_sclk, i_spi_ss_n, i_data};

assign o_data     = uo_pad[0];
assign o_spi_miso = uo_pad[1];

user_project_wrapper_2x2 u_wrapper (
    .io_clock_PAD (i_clk),
    .io_reset_PAD (i_rstn),
    .ui_PAD       (ui_pad),
    .uo_PAD       (uo_pad)
);

endmodule
