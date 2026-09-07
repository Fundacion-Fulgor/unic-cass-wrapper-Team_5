//=============================================================================
// Updated: 2026-09-01
// Fixed-point format converter for a complex sample. Discards NBF_INP-NBF_OUT
// fractional bits and saturates instead of wrapping when the value does not
// fit the output word. RND_MD selects truncation toward minus infinity or
// round to nearest with ties resolved to the even neighbour, matching the
// golden model in model/fft16.py.
//=============================================================================

module clip_round #(
    parameter NB_INP  = 32,
    parameter NBF_INP = 30,
    parameter NB_OUT  = 16,
    parameter NBF_OUT = 15,
    parameter RND_MD  =  1
) (
    `ifdef USE_POWER_PINS
    inout                      VPWR,
    inout                      VGND,
    `endif
    output signed [NB_OUT-1:0] o_data_re,
    output signed [NB_OUT-1:0] o_data_im,
    input  signed [NB_INP-1:0] i_data_re,
    input  signed [NB_INP-1:0] i_data_im
);

localparam SIGNED   = (NB_INP - NBF_INP) - (NB_OUT - NBF_OUT) + 1;
localparam BITS_DIS = NBF_INP - NBF_OUT;
localparam [NB_INP:0] RND_BIAS = (BITS_DIS > 0) ? ((1 << BITS_DIS) / 2 - 1) : 0;

wire signed [NB_OUT-1:0] rnd_re;
wire signed [NB_OUT-1:0] rnd_im;

generate
    case (RND_MD)
        0: begin : gen_trunc
            assign rnd_re = (~|i_data_re[NB_INP-1 -:SIGNED] || &i_data_re[NB_INP-1 -:SIGNED]) ?
                            i_data_re[(NB_INP-SIGNED)-:NB_OUT] :
                            (i_data_re[NB_INP-1]) ? {1'b1,{NB_OUT-1{1'b0}}} : {1'b0,{NB_OUT-1{1'b1}}};
            assign rnd_im = (~|i_data_im[NB_INP-1 -:SIGNED] || &i_data_im[NB_INP-1 -:SIGNED]) ?
                            i_data_im[(NB_INP-SIGNED)-:NB_OUT] :
                            (i_data_im[NB_INP-1]) ? {1'b1,{NB_OUT-1{1'b0}}} : {1'b0,{NB_OUT-1{1'b1}}};
        end

        1: begin : gen_round
            wire [NB_INP:0] sum_re;
            wire [NB_INP:0] sum_im;

            if (BITS_DIS > 0) begin : gen_add_round
                assign sum_re = {i_data_re[NB_INP-1], i_data_re}
                                + RND_BIAS
                                + {{NB_INP{1'b0}}, i_data_re[BITS_DIS]};
                assign sum_im = {i_data_im[NB_INP-1], i_data_im}
                                + RND_BIAS
                                + {{NB_INP{1'b0}}, i_data_im[BITS_DIS]};
            end
            else begin : gen_no_round
                assign sum_re = {i_data_re[NB_INP-1], i_data_re};
                assign sum_im = {i_data_im[NB_INP-1], i_data_im};
            end

            assign rnd_re = (~|sum_re[NB_INP -: SIGNED+1] || &sum_re[NB_INP -: SIGNED+1]) ?
                            sum_re[(NB_INP-SIGNED) -: NB_OUT] :
                            (sum_re[NB_INP]) ? {1'b1,{NB_OUT-1{1'b0}}} : {1'b0,{NB_OUT-1{1'b1}}};
            assign rnd_im = (~|sum_im[NB_INP -: SIGNED+1] || &sum_im[NB_INP -: SIGNED+1]) ?
                            sum_im[(NB_INP-SIGNED) -: NB_OUT] :
                            (sum_im[NB_INP]) ? {1'b1,{NB_OUT-1{1'b0}}} : {1'b0,{NB_OUT-1{1'b1}}};
        end

        default: begin : gen_default
            assign rnd_re = {NB_OUT{1'b0}};
            assign rnd_im = {NB_OUT{1'b0}};
        end
    endcase
endgenerate

assign o_data_re = rnd_re;
assign o_data_im = rnd_im;

endmodule
