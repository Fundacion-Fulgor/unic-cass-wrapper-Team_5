module user_project_example(
`ifdef USE_POWER_PINS
    inout VPWR,
    inout VGND,
`endif
    input  wire        clk_i,
    input  wire        rst_ni,
    input  wire [3:0] ui_PAD2CORE,
    output wire [10:0] uo_CORE2PAD
);

  

    scoreboard scoreboard_inst (
`ifdef USE_POWER_PINS
        .VPWR       (VPWR),
        .VGND       (VGND),
`endif

    .clk(clk_i),
    .reset(rst_ni),
    .team1_inc(ui_PAD2CORE[0]),
    .team2_inc(ui_PAD2CORE[1]),
    .team1_dec(ui_PAD2CORE[2]),
    .team2_dec(ui_PAD2CORE[3]),
    .seg_out(uo_CORE2PAD[6:0]),
    .seg_control(uo_CORE2PAD[10:7])
    );

endmodule
