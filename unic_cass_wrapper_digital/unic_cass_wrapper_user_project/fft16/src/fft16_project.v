module fft16_project(
    `ifdef USE_POWER_PINS
    inout               VPWR,  // Common digital supply
    inout               VGND,  // Common digital ground
    `endif
    input   wire        clk_i,
    input   wire        rst_ni,
    input   wire [16:0] ui_PAD2CORE,
    output  wire [16:0] uo_CORE2PAD
);

    wire [12:0] unused_input;

    assign unused_input      = ui_PAD2CORE[16:4];
    assign uo_CORE2PAD[16:2] = 15'b111111111111111;

    top_fft16 u_parallel_fft (
        `ifdef USE_POWER_PINS
        .VPWR       (VPWR),
        .VGND       (VGND),
        `endif
        .o_data     (uo_CORE2PAD[0]),
        .o_spi_miso (uo_CORE2PAD[1]),
        .i_data     (ui_PAD2CORE[0]),
        .i_spi_ss_n (ui_PAD2CORE[1]),
        .i_spi_sclk (ui_PAD2CORE[2]),
        .i_spi_mosi (ui_PAD2CORE[3]),
        .i_clk      (clk_i),
        .i_rst_n    (rst_ni)
    );

endmodule
