NB_DATA = 10
NB_TW = 10
NBF_TW = 9
NB_PROD = 21

DATA_MIN = -(1 << (NB_DATA - 1))
DATA_MAX = (1 << (NB_DATA - 1)) - 1
OUT_MIN = DATA_MIN
OUT_MAX = DATA_MAX

NBF_OUT = 6


def to_signed(value, bits):
    value = int(value) & ((1 << bits) - 1)
    if value >= (1 << (bits - 1)):
        value -= 1 << bits
    return value


def clip_round_rnd(value_int, nb_inp, nbf_inp, nb_out, nbf_out):
    signed_bits = (nb_inp - nbf_inp) - (nb_out - nbf_out) + 1
    bits_dis = nbf_inp - nbf_out
    width = nb_inp + 1
    if bits_dis > 0:
        bias = (1 << (bits_dis - 1)) - 1
        biased = value_int + bias + ((value_int >> bits_dis) & 1)
    else:
        biased = value_int
    raw = biased & ((1 << width) - 1)
    top = (raw >> (nb_inp - signed_bits)) & ((1 << (signed_bits + 1)) - 1)
    if top == 0 or top == (1 << (signed_bits + 1)) - 1:
        return to_signed(raw >> bits_dis, nb_out)
    if (raw >> nb_inp) & 1:
        return -(1 << (nb_out - 1))
    return (1 << (nb_out - 1)) - 1


def product(data_re, data_im, tw_re, tw_im):
    sum_re = data_re * tw_re - data_im * tw_im
    sum_im = data_re * tw_im + data_im * tw_re
    return to_signed(sum_re, NB_PROD), to_signed(sum_im, NB_PROD)


def expected(data_re, data_im, tw_re, tw_im):
    sum_re, sum_im = product(data_re, data_im, tw_re, tw_im)
    nbf_inp = NBF_OUT + NBF_TW
    return (
        clip_round_rnd(sum_re, NB_PROD, nbf_inp, NB_DATA, NBF_OUT),
        clip_round_rnd(sum_im, NB_PROD, nbf_inp, NB_DATA, NBF_OUT),
    )


def tw_from_angle(angle_index, n_points, inverse):
    import math

    sign = 1.0 if inverse else -1.0
    angle = sign * 2.0 * math.pi * angle_index / n_points
    scale = 2 ** NBF_TW
    re = int(round(math.cos(angle) * scale))
    im = int(round(math.sin(angle) * scale))
    re = max(DATA_MIN, min(DATA_MAX, re))
    im = max(DATA_MIN, min(DATA_MAX, im))
    return re, im
