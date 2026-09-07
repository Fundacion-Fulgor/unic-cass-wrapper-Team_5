//=============================================================================
// Updated: 2026-09-01
// Verification-only wrapper. Instantiates every clip_round configuration used
// by the design plus a few narrow ones, so a single elaboration can be swept
// exhaustively.
//=============================================================================

module clip_round_cfg (
    output signed [16-1:0] o_re0,
    output signed [16-1:0] o_im0,
    input  signed [32-1:0] i_re0,
    input  signed [32-1:0] i_im0,

    output signed [ 8-1:0] o_re1,
    output signed [ 8-1:0] o_im1,
    input  signed [12-1:0] i_re1,
    input  signed [12-1:0] i_im1,

    output signed [ 8-1:0] o_re2,
    output signed [ 8-1:0] o_im2,
    input  signed [12-1:0] i_re2,
    input  signed [12-1:0] i_im2,

    output signed [10-1:0] o_re3,
    output signed [10-1:0] o_im3,
    input  signed [21-1:0] i_re3,
    input  signed [21-1:0] i_im3,

    output signed [10-1:0] o_re4,
    output signed [10-1:0] o_im4,
    input  signed [21-1:0] i_re4,
    input  signed [21-1:0] i_im4,

    output signed [ 5-1:0] o_re5,
    output signed [ 5-1:0] o_im5,
    input  signed [ 8-1:0] i_re5,
    input  signed [ 8-1:0] i_im5,

    output signed [ 5-1:0] o_re6,
    output signed [ 5-1:0] o_im6,
    input  signed [ 8-1:0] i_re6,
    input  signed [ 8-1:0] i_im6,

    output signed [ 6-1:0] o_re7,
    output signed [ 6-1:0] o_im7,
    input  signed [10-1:0] i_re7,
    input  signed [10-1:0] i_im7,

    output signed [ 8-1:0] o_re8,
    output signed [ 8-1:0] o_im8,
    input  signed [ 8-1:0] i_re8,
    input  signed [ 8-1:0] i_im8
);

clip_round #(.NB_INP(32), .NBF_INP(30), .NB_OUT(16), .NBF_OUT(15), .RND_MD(1))
u_clip_round_0 (
    .o_data_re (o_re0),
    .o_data_im (o_im0),
    .i_data_re (i_re0),
    .i_data_im (i_im0)
);

clip_round #(.NB_INP(12), .NBF_INP(6), .NB_OUT(8), .NBF_OUT(3), .RND_MD(0))
u_clip_round_1 (
    .o_data_re (o_re1),
    .o_data_im (o_im1),
    .i_data_re (i_re1),
    .i_data_im (i_im1)
);

clip_round #(.NB_INP(12), .NBF_INP(7), .NB_OUT(8), .NBF_OUT(6), .RND_MD(0))
u_clip_round_2 (
    .o_data_re (o_re2),
    .o_data_im (o_im2),
    .i_data_re (i_re2),
    .i_data_im (i_im2)
);

clip_round #(.NB_INP(21), .NBF_INP(15), .NB_OUT(10), .NBF_OUT(6), .RND_MD(1))
u_clip_round_3 (
    .o_data_re (o_re3),
    .o_data_im (o_im3),
    .i_data_re (i_re3),
    .i_data_im (i_im3)
);

clip_round #(.NB_INP(21), .NBF_INP(12), .NB_OUT(10), .NBF_OUT(3), .RND_MD(1))
u_clip_round_4 (
    .o_data_re (o_re4),
    .o_data_im (o_im4),
    .i_data_re (i_re4),
    .i_data_im (i_im4)
);

clip_round #(.NB_INP(8), .NBF_INP(4), .NB_OUT(5), .NBF_OUT(2), .RND_MD(0))
u_clip_round_5 (
    .o_data_re (o_re5),
    .o_data_im (o_im5),
    .i_data_re (i_re5),
    .i_data_im (i_im5)
);

clip_round #(.NB_INP(8), .NBF_INP(4), .NB_OUT(5), .NBF_OUT(2), .RND_MD(1))
u_clip_round_6 (
    .o_data_re (o_re6),
    .o_data_im (o_im6),
    .i_data_re (i_re6),
    .i_data_im (i_im6)
);

clip_round #(.NB_INP(10), .NBF_INP(6), .NB_OUT(6), .NBF_OUT(3), .RND_MD(1))
u_clip_round_7 (
    .o_data_re (o_re7),
    .o_data_im (o_im7),
    .i_data_re (i_re7),
    .i_data_im (i_im7)
);

clip_round #(.NB_INP(8), .NBF_INP(6), .NB_OUT(8), .NBF_OUT(6), .RND_MD(1))
u_clip_round_8 (
    .o_data_re (o_re8),
    .o_data_im (o_im8),
    .i_data_re (i_re8),
    .i_data_im (i_im8)
);

endmodule
