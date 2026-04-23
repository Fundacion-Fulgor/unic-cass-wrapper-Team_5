// SPDX-FileCopyrightText: © 2025 Leo Moser
// SPDX-License-Identifier: Apache-2.0

module user_project_wrapper_2x2 (
    inout wire io_clock_PAD,
    inout wire io_reset_PAD,
    inout wire [16:0] ui_PAD,
    inout wire [16:0] uo_PAD
);
    wire io_clock_p2c;
    wire io_reset_p2c;
    wire [16:0] ui_PAD2CORE;
    wire [16:0] uo_CORE2PAD;

    (*keep*)
    wire [1:0] unused_input;

    assign unused_input = ui_PAD2CORE[16:15];

    // Power/ground pad instances
    generate
    for (genvar i=0; i<4; i++) begin : iovdd_pads
        (* keep *)
        sg13g2_IOPadIOVdd iovdd_pad  (
            `ifdef USE_POWER_PINS
            .iovdd  (IOVDD),
            .iovss  (IOVSS),
            .vdd    (VDD),
            .vss    (VSS)
            `endif
        );
    end
    for (genvar i=0; i<4; i++) begin : iovss_pads
        (* keep *)
        sg13g2_IOPadIOVss iovss_pad  (
            `ifdef USE_POWER_PINS
            .iovdd  (IOVDD),
            .iovss  (IOVSS),
            .vdd    (VDD),
            .vss    (VSS)
            `endif
        );
    end
    for (genvar i=0; i<4; i++) begin : vdd_pads
        (* keep *)
        sg13g2_IOPadVdd vdd_pad  (
            `ifdef USE_POWER_PINS
            .iovdd  (IOVDD),
            .iovss  (IOVSS),
            .vdd    (VDD),
            .vss    (VSS)
            `endif
        );
    end
    for (genvar i=0; i<4; i++) begin : vss_pads
        (* keep *)
        sg13g2_IOPadVss vss_pad  (
            `ifdef USE_POWER_PINS
            .iovdd  (IOVDD),
            .iovss  (IOVSS),
            .vdd    (VDD),
            .vss    (VSS)
            `endif
        );
    end
    endgenerate

    sg13g2_IOPadIn sg13g2_IOPad_io_clock (
        `ifdef USE_POWER_PINS
        .vss    (VSS),
        .vdd    (VDD),
        .iovss  (IOVSS),
        .iovdd  (IOVDD),
        `endif
        .p2c (io_clock_p2c), //o
        .pad (io_clock_PAD)  //~
    );

    sg13g2_IOPadIn sg13g2_IOPad_io_reset (
        `ifdef USE_POWER_PINS
        .vss    (VSS),
        .vdd    (VDD),
        .iovss  (IOVSS),
        .iovdd  (IOVDD),
        `endif
        .p2c (io_reset_p2c), //o
        .pad (io_reset_PAD)  //~
    );

    generate
    for (genvar i=0; i<17; i++) begin : sg13g2_IOPadIn_ui
        sg13g2_IOPadIn ui (
            `ifdef USE_POWER_PINS
            .vss    (VSS),
            .vdd    (VDD),
            .iovss  (IOVSS),
            .iovdd  (IOVDD),
            `endif
            .p2c (ui_PAD2CORE[i]),
            .pad (ui_PAD[i])
        );
    end
    endgenerate

    generate
    for (genvar i=0; i<17; i++) begin : sg13g2_IOPadOut30mA_uo
        sg13g2_IOPadOut30mA uo (
            `ifdef USE_POWER_PINS
            .vss    (VSS),
            .vdd    (VDD),
            .iovss  (IOVSS),
            .iovdd  (IOVDD),
            `endif
            .c2p (uo_CORE2PAD[i]),
            .pad (uo_PAD[i])
        );
    end
    endgenerate

    fft16_project fft16_project_inst (
        .clk_i        (io_clock_p2c),
        .rst_ni       (io_reset_p2c),
        .ui_PAD2CORE  (ui_PAD2CORE[3:0]),
        .uo_CORE2PAD  (uo_CORE2PAD[1:0])
    );

    fpga fpga_top_inst (                    
        .clk_i        (io_clock_p2c),
        .rst_ni       (io_reset_p2c),
        .ui_PAD2CORE  (ui_PAD2CORE[6:4]),
        .uo_CORE2PAD  (uo_CORE2PAD[2:2])
    );

    user_project user_project_inst ( //clock generator
        .clk_i        (io_clock_p2c),
        .rst_ni       (io_reset_p2c),
        .ui_PAD2CORE  (ui_PAD2CORE[10:7]),
        .uo_CORE2PAD  (uo_CORE2PAD[5:3])
    );

    user_project_example user_project_example_inst ( //DSIC
        .clk_i        (io_clock_p2c),
        .rst_ni       (io_reset_p2c),
        .ui_PAD2CORE  (ui_PAD2CORE[14:11]),
        .uo_CORE2PAD  (uo_CORE2PAD[16:6])
    );

endmodule


