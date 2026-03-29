module user_project_example(
`ifdef USE_POWER_PINS
    inout VPWR,
    inout VGND,
`endif
    input  wire        clk_i,
    input  wire        rst_ni,
    input  wire [14:11] ui_PAD2CORE,
    output wire [16:6] uo_CORE2PAD
);

  

    scoreboard scoreboard_inst (
`ifdef USE_POWER_PINS
        .VPWR       (VPWR),
        .VGND       (VGND),
`endif

    .clk(clk_i),
    .reset(rst_ni),
    .team1_inc(ui_PAD2CORE[11]),
    .team2_inc(ui_PAD2CORE[12]),
    .team1_dec(ui_PAD2CORE[13]),
    .team2_dec(ui_PAD2CORE[14]),
    .seg_out(uo_CORE2PAD[12:6]),
    .seg_control(uo_CORE2PAD[16:13])
    );

endmodule
