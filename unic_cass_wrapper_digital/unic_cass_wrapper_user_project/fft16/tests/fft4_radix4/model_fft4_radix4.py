NB_INPUT = 8
NB_STAGE = NB_INPUT + 2
NB_TW = 10
NBF_TW = 9
NB_PROD = 21

TW_RE_HEX = [
    0x1FF, 0x1D9, 0x16A, 0x0C4, 0x000, 0x33C, 0x296, 0x227,
    0x200, 0x227, 0x296, 0x33C, 0x000, 0x0C4, 0x16A, 0x1D9,
]

TW_IM_FFT_HEX = [
    0x000, 0x33C, 0x296, 0x227, 0x200, 0x227, 0x296, 0x33C,
    0x000, 0x0C4, 0x16A, 0x1D9, 0x1FF, 0x1D9, 0x16A, 0x0C4,
]

TW_IM_IFFT_HEX = [
    0x000, 0x0C4, 0x16A, 0x1D9, 0x1FF, 0x1D9, 0x16A, 0x0C4,
    0x000, 0x33C, 0x296, 0x227, 0x200, 0x227, 0x296, 0x33C,
]


def to_signed(value, bits):
    value = int(value) & ((1 << bits) - 1)
    if value >= (1 << (bits - 1)):
        value -= 1 << bits
    return value


TW_RE = [to_signed(v, NB_TW) for v in TW_RE_HEX]
TW_IM_FFT = [to_signed(v, NB_TW) for v in TW_IM_FFT_HEX]
TW_IM_IFFT = [to_signed(v, NB_TW) for v in TW_IM_IFFT_HEX]


def twiddle(index, inverse):
    index &= 0x0F
    return TW_RE[index], (TW_IM_IFFT if inverse else TW_IM_FFT)[index]


def clip_round_rnd(value_int, nb_inp, bits_dis, signed_bits, nb_out):
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


def complex_multiply(data, tw_re, tw_im):
    sum_re = to_signed(int(data.real) * tw_re - int(data.imag) * tw_im, NB_PROD)
    sum_im = to_signed(int(data.real) * tw_im + int(data.imag) * tw_re, NB_PROD)
    return complex(
        clip_round_rnd(sum_re, NB_PROD, NBF_TW, 3, NB_TW),
        clip_round_rnd(sum_im, NB_PROD, NBF_TW, 3, NB_TW),
    )


def butterfly(x0, x1, x2, x3, inverse):
    ev_sum = x0 + x2
    ev_sub = x0 - x2
    od_sum = x1 + x3
    od_sub = x1 - x3
    y0 = ev_sum + od_sum
    y2 = ev_sum - od_sum
    if inverse:
        y1 = complex(ev_sub.real - od_sub.imag, ev_sub.imag + od_sub.real)
        y3 = complex(ev_sub.real + od_sub.imag, ev_sub.imag - od_sub.real)
    else:
        y1 = complex(ev_sub.real + od_sub.imag, ev_sub.imag - od_sub.real)
        y3 = complex(ev_sub.real - od_sub.imag, ev_sub.imag + od_sub.real)
    return [
        complex(to_signed(int(v.real), NB_STAGE), to_signed(int(v.imag), NB_STAGE))
        for v in (y0, y1, y2, y3)
    ]


def process_group(group, m, inverse):
    y = butterfly(group[0], group[1], group[2], group[3], inverse)
    indices = [0, m & 0x0F, (2 * m) & 0x0F, (3 * m) & 0x0F]
    return [complex_multiply(y[k], *twiddle(indices[k], inverse)) for k in range(4)]


def process_block(samples, inverse):
    out = []
    for m in range(4):
        group = [samples[m], samples[m + 4], samples[m + 8], samples[m + 12]]
        out.append(process_group(group, m, inverse))
    return out
