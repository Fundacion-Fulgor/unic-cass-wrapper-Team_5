// SPDX-FileCopyrightText: © 2025 Leo Moser
// SPDX-License-Identifier: Apache-2.0
module user_project(
    `ifdef USE_POWER_PINS
    inout VPWR,    // Common digital supply
    inout VGND,    // Common digital ground
    `endif
    input  wire clk_i,
    input  wire rst_ni,
    input  wire [16:0] ui_PAD2CORE,
    output wire [16:0] uo_CORE2PAD
);
    wire io_clock_p2c;
    wire io_reset_p2c;


    wire w_osc      = ui_PAD2CORE[0];
    wire w_spi_sck  = ui_PAD2CORE[1];
    wire w_spi_cs_n = ui_PAD2CORE[2];
    wire w_spi_mosi = ui_PAD2CORE[3];

    wire w_spi_miso;
    wire [1:0] w_clockp;

    assign uo_CORE2PAD[0] = w_spi_miso;
    assign uo_CORE2PAD[2:1] = w_clockp;
    
    assign uo_CORE2PAD[16:3] = 14'h3FFF;

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


