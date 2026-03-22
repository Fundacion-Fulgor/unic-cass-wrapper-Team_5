module fabric_2x2 (
    input  wire clk,
    input  wire rst_n,
    input  wire [51:0] config_bits,
    input  wire [1:0] user_inputs,
    output wire user_output
);

    wire [12:0] config_00 = config_bits[12:0];
    wire [12:0] config_01 = config_bits[25:13];
    wire [12:0] config_10 = config_bits[38:26];
    wire [12:0] config_11 = config_bits[51:39];

    wire h_00_to_01;
    wire h_01_to_00;
    wire h_10_to_11;
    wire h_11_to_10;

    wire v_00_to_10;
    wire v_10_to_00;
    wire v_01_to_11;
    wire v_11_to_01;

    wire out_00, out_01, out_10, out_11;

    clb clb_00 (
        .clk_i(clk),
        .rst_ni(rst_n),
        .from_north(1'b0),
        .from_south(v_10_to_00),
        .from_east(h_01_to_00),
        .from_west(1'b0),
        .local_inputs(user_inputs),
        .confi(config_00),
        .to_north(),
        .to_south(v_00_to_10),
        .to_east(h_00_to_01),
        .to_west(),
        .local_output(out_00)
    );

    clb clb_01 (
        .clk_i(clk),
        .rst_ni(rst_n),
        .from_north(1'b0),
        .from_south(v_11_to_01),
        .from_east(1'b0),
        .from_west(h_00_to_01),
        .local_inputs(user_inputs),
        .confi(config_01),
        .to_north(),
        .to_south(v_01_to_11),
        .to_east(),
        .to_west(h_01_to_00),
        .local_output(out_01)
    );

    clb clb_10 (
        .clk_i(clk),
        .rst_ni(rst_n),
        .from_north(v_00_to_10),
        .from_south(1'b0),
        .from_east(h_11_to_10),
        .from_west(1'b0),
        .local_inputs(user_inputs),
        .confi(config_10),
        .to_north(v_10_to_00),
        .to_south(),
        .to_east(h_10_to_11),
        .to_west(),
        .local_output(out_10)
    );

    clb clb_11 (
        .clk_i(clk),
        .rst_ni(rst_n),
        .from_north(v_01_to_11),
        .from_south(1'b0),
        .from_east(1'b0),
        .from_west(h_10_to_11),
        .local_inputs(user_inputs),
        .confi(config_11),
        .to_north(v_11_to_01),
        .to_south(),
        .to_east(),
        .to_west(h_11_to_10),
        .local_output(out_11)
    );

    assign user_output = out_11;

endmodule
