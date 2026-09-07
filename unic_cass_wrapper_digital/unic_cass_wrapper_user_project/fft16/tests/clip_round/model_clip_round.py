from fxpmath import Fxp


class ROUND:
    def __init__(self, rounding='floor'):
        """
        rounding: 'floor', 'around'
        """
    def rnd(self, val, signed, n_word, n_frac, rouding):
        fxp_val = Fxp(val,
                      signed=signed,
                      n_word=n_word,
                      n_frac=n_frac,
                      rounding=rouding,
                      overflow='saturate')
        return fxp_val.get_val()

    def crnd(self, val, signed, n_word, n_frac, rounding):
        q_r = self.rnd(val.real, signed, n_word, n_frac, rounding)
        q_i = self.rnd(val.imag, signed, n_word, n_frac, rounding)
        return complex(q_r, q_i)

    def crnd_vec(self, val_vec, signed, n_word, n_frac, rounding):
        result_list = [self.crnd(v, signed, n_word, n_frac, rounding) for v in val_vec]
        return result_list


class ClipRoundConfig:
    def __init__(self, nb_inp, nbf_inp, nb_out, nbf_out, rnd_md):
        self.nb_inp = nb_inp
        self.nbf_inp = nbf_inp
        self.nb_out = nb_out
        self.nbf_out = nbf_out
        self.rnd_md = rnd_md
        self.signed_bits = (nb_inp - nbf_inp) - (nb_out - nbf_out) + 1
        self.bits_dis = nbf_inp - nbf_out
        self.in_min = -(1 << (nb_inp - 1))
        self.in_max = (1 << (nb_inp - 1)) - 1
        self.out_min = -(1 << (nb_out - 1))
        self.out_max = (1 << (nb_out - 1)) - 1

    def apply(self, value_int):
        if self.rnd_md == 0:
            raw = value_int & ((1 << self.nb_inp) - 1)
            top = (raw >> (self.nb_inp - self.signed_bits)) & ((1 << self.signed_bits) - 1)
            if top == 0 or top == (1 << self.signed_bits) - 1:
                return _to_signed(raw >> self.bits_dis, self.nb_out)
            return self.out_min if (raw >> (self.nb_inp - 1)) & 1 else self.out_max

        width = self.nb_inp + 1
        biased = value_int
        if self.bits_dis > 0:
            bias = (1 << (self.bits_dis - 1)) - 1
            biased = value_int + bias + ((value_int >> self.bits_dis) & 1)
        raw = biased & ((1 << width) - 1)
        top = (raw >> (self.nb_inp - self.signed_bits)) & ((1 << (self.signed_bits + 1)) - 1)
        if top == 0 or top == (1 << (self.signed_bits + 1)) - 1:
            return _to_signed(raw >> self.bits_dis, self.nb_out)
        return self.out_min if (raw >> self.nb_inp) & 1 else self.out_max

    def ideal_float(self, value_int):
        return value_int / (2 ** self.nbf_inp)

    def out_float(self, value_int):
        return value_int / (2 ** self.nbf_out)

    def lsb_out(self):
        return 2.0 ** (-self.nbf_out)

    def sat_low_int(self):
        return self.out_min << self.bits_dis

    def sat_high_int(self):
        return (self.out_max << self.bits_dis) + ((1 << self.bits_dis) - 1)


def _to_signed(value, bits):
    value &= (1 << bits) - 1
    if value >= (1 << (bits - 1)):
        value -= 1 << bits
    return value


def to_signed(value, bits):
    return _to_signed(int(value), bits)
