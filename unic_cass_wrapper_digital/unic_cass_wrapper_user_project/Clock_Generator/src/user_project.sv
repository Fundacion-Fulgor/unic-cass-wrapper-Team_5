// SPDX-FileCopyrightText: © 2025 Leo Moser
// SPDX-License-Identifier: Apache-2.0
module user_project(
    `ifdef USE_POWER_PINS
    inout VPWR,    // Common digital supply
    inout VGND,    // Common digital ground
    `endif
    input  wire clk_i,
    input  wire rst_ni,
    input  wire [10:7] ui_PAD2CORE,
    output wire [5:3] uo_CORE2PAD
);
    wire io_clock_p2c;
    wire io_reset_p2c;


    wire w_osc      = ui_PAD2CORE[7];
    wire w_spi_sck  = ui_PAD2CORE[8];
    wire w_spi_cs_n = ui_PAD2CORE[9];
    wire w_spi_mosi = ui_PAD2CORE[10];

    wire w_spi_miso;
    wire [1:0] w_clockp;

    assign uo_CORE2PAD[3] = w_spi_miso;
    assign uo_CORE2PAD[5:4] = w_clockp;
    

    (* keep_hierarchy *)
    spi_digital_pll_wrapper pll_inst (
        `ifdef USE_POWER_PINS
        .VPWR(VPWR),
        .VGND(VGND),
        `endif
        .resetb(rst_ni),
        .osc(w_osc),
        .spi_sck(w_spi_sck),
        .spi_cs_n(w_spi_cs_n),
        .spi_mosi(w_spi_mosi),
        .spi_miso(w_spi_miso),
        .clockp(w_clockp)
    );

endmodule

