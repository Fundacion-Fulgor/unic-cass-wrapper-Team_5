module clip_round#(
    parameter   NB_INP  = 32,
    parameter   NBF_INP = 30,
    parameter   NB_OUT  = 16,
    parameter   NBF_OUT = 15,
    parameter   RND_MD  =  1  // 0: SAT-TRUNC, 1: SAT-ROUND
)
(
    `ifdef USE_POWER_PINS
    inout               VPWR,  // Common digital supply
    inout               VGND,  // Common digital ground
    `endif
    input  signed [NB_INP-1:0] i_data_re,
    input  signed [NB_INP-1:0] i_data_im,
    output signed [NB_OUT-1:0] o_data_re,
    output signed [NB_OUT-1:0] o_data_im
);

///////////////////////////////////////////////////////////////////////////////
// WIRE AND REGISTER
///////////////////////////////////////////////////////////////////////////////

localparam SIGNED = (NB_INP - NBF_INP) - (NB_OUT - NBF_OUT) + 1;
localparam BITS_DIS = NBF_INP - NBF_OUT;

wire signed [NB_INP-1:0] w_data_re;
wire signed [NB_INP-1:0] w_data_im;
wire signed [NB_OUT-1:0] w_rnd_re;
wire signed [NB_OUT-1:0] w_rnd_im;

///////////////////////////////////////////////////////////////////////////////
// COMBINATIONAL LOGIC
///////////////////////////////////////////////////////////////////////////////

assign w_data_re = i_data_re;
assign w_data_im = i_data_im;

generate
    case (RND_MD)
        0: begin: gen_trunc
            assign w_rnd_re = (~|w_data_re[NB_INP-1 -:SIGNED] || &w_data_re[NB_INP-1 -:SIGNED]) ?
                              w_data_re[(NB_INP-SIGNED)-:NB_OUT] :
                             (w_data_re[NB_INP-1]) ? {1'b1,{NB_OUT-1{1'b0}}} : {1'b0,{NB_OUT-1{1'b1}}};
            assign w_rnd_im = (~|w_data_im[NB_INP-1 -:SIGNED] || &w_data_im[NB_INP-1 -:SIGNED]) ?
                              w_data_im[(NB_INP-SIGNED)-:NB_OUT] :
                             (w_data_im[NB_INP-1]) ? {1'b1,{NB_OUT-1{1'b0}}} : {1'b0,{NB_OUT-1{1'b1}}};
        end
        1: begin : gen_round
            wire [NB_INP:0] data_plus_round_re;
            wire [NB_INP:0] data_plus_round_im;

            if (BITS_DIS > 0) begin : gen_add_round
                assign data_plus_round_re = {i_data_re[NB_INP-1], i_data_re} + ({{NB_INP{1'b0}}, 1'b1} << (BITS_DIS - 1));
                assign data_plus_round_im = {i_data_im[NB_INP-1], i_data_im} + ({{NB_INP{1'b0}}, 1'b1} << (BITS_DIS - 1));
            end else begin : gen_no_round
                assign data_plus_round_re = {i_data_re[NB_INP-1], i_data_re};
                assign data_plus_round_im = {i_data_im[NB_INP-1], i_data_im};
            end
            assign w_rnd_re = (~|data_plus_round_re[NB_INP -: SIGNED+1] || &data_plus_round_re[NB_INP -: SIGNED+1]) ?
                              data_plus_round_re[(NB_INP-SIGNED) -: NB_OUT] :
                              (data_plus_round_re[NB_INP]) ? {1'b1,{NB_OUT-1{1'b0}}} : {1'b0,{NB_OUT-1{1'b1}}};

            assign w_rnd_im = (~|data_plus_round_im[NB_INP -: SIGNED+1] || &data_plus_round_im[NB_INP -: SIGNED+1]) ?
                              data_plus_round_im[(NB_INP-SIGNED) -: NB_OUT] :
                              (data_plus_round_im[NB_INP]) ? {1'b1,{NB_OUT-1{1'b0}}} : {1'b0,{NB_OUT-1{1'b1}}};
            end

            default: begin : gen_default
                assign w_rnd_re = {NB_OUT{1'b0}};
                assign w_rnd_im = {NB_OUT{1'b0}};
            end
    endcase
endgenerate

assign o_data_re = w_rnd_re;
assign o_data_im = w_rnd_im;

endmodule
