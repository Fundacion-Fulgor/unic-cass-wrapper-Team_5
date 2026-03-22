module clb (
    input  wire clk_i,
    input  wire rst_ni,

    input  wire from_north,
    input  wire from_south,
    input  wire from_east,
    input  wire from_west,

    input  wire [1:0] local_inputs,

    input  wire [12:0] confi,

    output wire to_north,
    output wire to_south,
    output wire to_east,
    output wire to_west,

    output wire local_output
);

    wire [1:0] mode         = confi[1:0];
    wire [2:0] A_input_sel  = confi[4:2];
    wire [2:0] B_input_sel  = confi[7:5];
    wire [3:0] output_route = confi[11:8];
    wire       use_ff       = confi[12];

    wire [5:0] input_sources = {
        local_inputs[1],
        local_inputs[0],
        from_west,
        from_east,
        from_south,
        from_north
    };

    wire A = input_sources[A_input_sel[2:0]];
    wire B = input_sources[B_input_sel[2:0]];

    reg [3:0] lut_config;
    always @(*) begin
        case (mode)
            2'b00: lut_config = 4'b1000;
            2'b01: lut_config = 4'b1110;
            2'b10: lut_config = 4'b0110;
            2'b11: lut_config = 4'b1010;
        endcase
    end

    wire lut_out = lut_config[{A, B}];

    reg ff_out;
    always @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni)
            ff_out <= 1'b0;
        else
            ff_out <= lut_out;
    end

    wire Y = use_ff ? ff_out : lut_out;

    assign to_north     = output_route[0] ? Y : 1'b0;
    assign to_south     = output_route[1] ? Y : 1'b0;
    assign to_east      = output_route[2] ? Y : 1'b0;
    assign to_west      = output_route[3] ? Y : 1'b0;
    assign local_output = Y;

endmodule
