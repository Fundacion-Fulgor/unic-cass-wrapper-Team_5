import numpy as np
from fxpmath import Fxp

class ROUND:
    def __init__(self):
        pass

    def rnd(self, val, signed, n_word, n_frac, rounding):
        fxp_val = Fxp(val, signed=signed, n_word=n_word, n_frac=n_frac, 
                      rounding=rounding, overflow='saturate')
        return fxp_val.get_val()

    def crnd(self, val, signed, n_word, n_frac, rounding):
        q_r = self.rnd(val.real, signed, n_word, n_frac, rounding)
        q_i = self.rnd(val.imag, signed, n_word, n_frac, rounding)
        return complex(q_r, q_i)

class FFT4_Reference:
    def __init__(self, NB_INPUT=8, NBF_INPUT=6, inverse=False):
        self.round = ROUND()
        self.inverse = inverse

        self.nb_in = NB_INPUT
        self.nbf_in = NBF_INPUT
        
        self.nb_st1 = NB_INPUT + 1
        self.nbf_st1 = NBF_INPUT
        
        self.nb_out = NB_INPUT + 2
        self.nbf_out = NBF_INPUT

    def process(self, x):
        b0, b1, b2, b3 = x[0], x[1], x[2], x[3]

        v0 = b0 + b2
        v1 = b0 - b2
        v2 = b1 + b3
        v3 = b1 - b3

        v0 = self.round.crnd(v0, True, self.nb_st1, self.nbf_st1, 'trunc')
        v1 = self.round.crnd(v1, True, self.nb_st1, self.nbf_st1, 'trunc')
        v2 = self.round.crnd(v2, True, self.nb_st1, self.nbf_st1, 'trunc')
        v3 = self.round.crnd(v3, True, self.nb_st1, self.nbf_st1, 'trunc')

        if self.inverse == 0:
            v3_fix = complex(v3.imag, -v3.real)
        else:
            v3_fix = complex(-v3.imag, v3.real)
        
        v3 = v3_fix

        # --- Stage 2 ---
        y0 = v0 + v2
        y1 = v1 + v3
        y2 = v0 - v2
        y3 = v1 - v3

        y0 = self.round.crnd(y0, True, self.nb_out, self.nbf_out, 'trunc')
        y1 = self.round.crnd(y1, True, self.nb_out, self.nbf_out, 'trunc')
        y2 = self.round.crnd(y2, True, self.nb_out, self.nbf_out, 'trunc')
        y3 = self.round.crnd(y3, True, self.nb_out, self.nbf_out, 'trunc')

        # return [y0, y1, y2, y3]
        stage1_out = [v0, v1, v2, v3]
        stage2_out = [y0, y1, y2, y3]
        return stage1_out, stage2_out