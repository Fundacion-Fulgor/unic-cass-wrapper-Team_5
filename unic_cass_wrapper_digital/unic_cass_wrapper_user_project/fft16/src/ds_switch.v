module ds_switch #(
    parameter NB = 8
) (
    `ifdef USE_POWER_PINS
    inout               VPWR,  // Common digital supply
    inout               VGND,  // Common digital ground
    `endif
    input               i_clk,
    input               i_rst_n,
    input               i_valid,
    input  [NB - 1 : 0] i_data_0r,
    input  [NB - 1 : 0] i_data_0i,
    input  [NB - 1 : 0] i_data_1r,
    input  [NB - 1 : 0] i_data_1i,
    //-------------------------------
    output              o_valid,
    output [NB - 1 : 0] o_data_0r,
    output [NB - 1 : 0] o_data_0i,
    output [NB - 1 : 0] o_data_1r,
    output [NB - 1 : 0] o_data_1i
);

////////////////////////////////////////////////////////////
// WIRE AND REGISTER
////////////////////////////////////////////////////////////

reg  [NB-1:0] mem_0r;
reg  [NB-1:0] mem_0i;
reg  [NB-1:0] mem_1r;
reg  [NB-1:0] mem_1i;
reg  [NB-1:0] mem_2r;
reg  [NB-1:0] mem_2i;
reg  [NB-1:0] mem_3r;
reg  [NB-1:0] mem_3i;
//---------------------------------------------
reg  [NB-1:0] r_data_0r;
reg  [NB-1:0] r_data_0i;
reg  [NB-1:0] r_data_1r;
reg  [NB-1:0] r_data_1i;
//---------------------------------------------
reg           r_valid;
reg  [2-1:0]  count;
reg           transmitting;


////////////////////////////////////////////////////////////
// CL && REG
////////////////////////////////////////////////////////////

always @(posedge i_clk) begin  
  if (!i_rst_n) begin
    count <= 2'd0;
    transmitting <= 1'b0;
    r_valid <= 1'b0;
  end else begin
    if (i_valid) begin
        if (count == 2'd0) begin
            mem_0r <= i_data_0r;
            mem_0i <= i_data_0i;
            mem_2r <= i_data_1r;
            mem_2i <= i_data_1i;
            count <= 2'd1;
        end else if (count == 2'd1) begin
            mem_1r <= i_data_0r;
            mem_1i <= i_data_0i;
            mem_3r <= i_data_1r;
            mem_3i <= i_data_1i;
            count <= 2'd0;
            transmitting <= 1'b1;
        end
    end

    if (transmitting) begin
        if (count == 2'd0) begin
          r_data_0r <= mem_0r; r_data_0i <= mem_0i;
          r_data_1r <= mem_1r; r_data_1i <= mem_1i;
          r_valid   <= 1'b1;
          count <= count + 2'd1;
        end else begin
          r_data_0r <= mem_2r; r_data_0i <= mem_2i;
          r_data_1r <= mem_3r; r_data_1i <= mem_3i;
          r_valid   <= 1'b1;
          count <= count + 2'd1;
          transmitting <= 1'b0;
        end
    end else begin
      r_valid   <= 1'b0;
      if (count == 2'd3) begin
        count <= 2'd0;
      end
    end
  end
end

assign o_data_0r = r_data_0r;
assign o_data_0i = r_data_0i;
assign o_data_1r = r_data_1r;
assign o_data_1i = r_data_1i;
assign o_valid = r_valid;

endmodule
