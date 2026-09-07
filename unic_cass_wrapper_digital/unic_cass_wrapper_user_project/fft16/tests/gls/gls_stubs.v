//=============================================================================
// Updated: 2026-09-07
// Verification-only stubs for the three sibling projects sharing the 2x2
// wrapper and for the bondpad cell. Their sources are not part of this
// repository, so gate level simulation of the wrapper substitutes empty blocks
// that drive their outputs low: a wrapper level short between their pins and
// the FFT pins would show up as a conflict instead of being masked.
//=============================================================================

module fpga (
    input  wire       clk_i,
    input  wire       rst_ni,
    input  wire [2:0] ui_PAD2CORE,
    output wire [0:0] uo_CORE2PAD
);

assign uo_CORE2PAD = 1'b0;

endmodule

module user_project (
    input  wire       clk_i,
    input  wire       rst_ni,
    input  wire [3:0] ui_PAD2CORE,
    output wire [2:0] uo_CORE2PAD
);

assign uo_CORE2PAD = 3'b0;

endmodule

module user_project_example (
    input  wire        clk_i,
    input  wire        rst_ni,
    input  wire [3:0]  ui_PAD2CORE,
    output wire [10:0] uo_CORE2PAD
);

assign uo_CORE2PAD = 11'b0;

endmodule

module bondpad_70x70_novias (
    inout wire pad
);

endmodule
