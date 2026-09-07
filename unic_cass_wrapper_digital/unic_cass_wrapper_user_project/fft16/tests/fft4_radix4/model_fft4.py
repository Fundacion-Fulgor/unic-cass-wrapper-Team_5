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
    
    def crnd_vec(self, val_vec, signed, n_word, n_frac, rounding):
        result_list = [self.crnd(v, signed, n_word, n_frac, rounding) for v in val_vec]
        return result_list   

class FFT4_Reference:
    def __init__(self, NB_INPUT=8, NBF_INPUT=6, inverse=False):
        self.round = ROUND()
        self.inverse = inverse
        self.N       = 16

        self.nb_in      = NB_INPUT
        self.nbf_in     = NBF_INPUT
        self.nb_st1     = self.nb_in + 2
        self.nbf_st1    = self.nbf_in
        self.nb_out     = self.nb_st1
        self.nbf_out    = self.nbf_st1

        self.nb_tw   = 10
        self.nbf_tw  =  9
        self.tw_sign  = -1 if self.inverse == 0 else +1
        tw_float = np.exp(self.tw_sign * 1j * 2 * np.pi * np.arange(self.N) / self.N)
        tw_fxp = self.round.crnd_vec(val_vec = tw_float, signed=True,  n_word=self.nb_tw, n_frac=self.nbf_tw, rounding='around')
        self.TW16 = tw_fxp

    def fft4_radix4_buttefly(self, x):
        s0, s1, s2, s3 = x[0], x[1], x[2], x[3]
        
        y0_real = s0.real + s1.real + s2.real + s3.real
        y0_imag = s0.imag + s1.imag + s2.imag + s3.imag
        y0 = complex(y0_real, y0_imag)

        y2_real = s0.real - s1.real + s2.real - s3.real
        y2_imag = s0.imag - s1.imag + s2.imag - s3.imag
        y2 = complex(y2_real, y2_imag)

        if self.inverse == 0:
            y1_real = s0.real + s1.imag - s2.real - s3.imag
            y1_imag = s0.imag - s1.real - s2.imag + s3.real
            y1 = complex(y1_real, y1_imag)

            y3_real = s0.real - s1.imag - s2.real + s3.imag
            y3_imag = s0.imag + s1.real - s2.imag - s3.real
            y3 = complex(y3_real, y3_imag)
        else:
            y1_real = s0.real - s1.imag - s2.real + s3.imag
            y1_imag = s0.imag + s1.real - s2.imag - s3.real
            y1 = complex(y1_real, y1_imag)

            y3_real = s0.real + s1.imag - s2.real - s3.imag
            y3_imag = s0.imag - s1.real - s2.imag + s3.real
            y3 = complex(y3_real, y3_imag)

        y0 = self.round.crnd(val=y0, signed=True, n_word=self.nb_st1, n_frac=self.nbf_st1, rounding='trunc')
        y1 = self.round.crnd(val=y1, signed=True, n_word=self.nb_st1, n_frac=self.nbf_st1, rounding='trunc')
        y2 = self.round.crnd(val=y2, signed=True, n_word=self.nb_st1, n_frac=self.nbf_st1, rounding='trunc')
        y3 = self.round.crnd(val=y3, signed=True, n_word=self.nb_st1, n_frac=self.nbf_st1, rounding='trunc')
        result = [y0, y1, y2, y3]
        
        return result

    def process(self, x):
        h_result = [0.0 + 1j*0.0] * self.N

        for m in range(int(self.N/4)):
            input_select = [x[m], x[m+4], x[m+8], x[m+12]]
            result_butterfly = self.fft4_radix4_buttefly(input_select)
            for k in range(int(self.N/4)):
                idx = (m * 4) + k
                value = result_butterfly[k] * self.TW16[m * k]
                h_result[idx] = self.round.crnd(val=value, signed=True, n_word=self.nb_out, n_frac=self.nbf_out, rounding='around')
        return h_result