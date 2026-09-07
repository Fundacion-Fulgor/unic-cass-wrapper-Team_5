import numpy as np
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

class FFT16:
    def __init__(self, N=16, fxp=0, NB_INPUT=8, NBF_INPUT=6, fft_mode=1):
        self.fxp      = fxp
        self.N        = N
        self.round    = ROUND()
        self.fft_mode = fft_mode
        self.tw_sign  = -1 if fft_mode == 1 else +1

        self.nb_i    = NB_INPUT
        self.nbf_i   = NBF_INPUT
        self.nb_tw   = 10
        self.nbf_tw  =  9
        self.nb_st1  = self.nb_i+2
        self.nbf_st1 = self.nbf_i
        self.nb_st2  = self.nb_st1
        self.nbf_st2 = self.nbf_st1
        self.nb_out  = NB_INPUT
        self.nbf_out = NBF_INPUT-3 if fft_mode == 1 else NBF_INPUT+3
        if self.fxp == 0:
            self.TW16 = np.exp(self.tw_sign * 1j * 2 * np.pi * np.arange(self.N) / self.N)
        else:
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

        if self.fft_mode == 1:
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

        if self.fxp == 0:
            result = [y0, y1, y2, y3]
        else:
            y0 = self.round.crnd(val=y0, signed=True, n_word=self.nb_st1, n_frac=self.nbf_st1, rounding='floor')
            y1 = self.round.crnd(val=y1, signed=True, n_word=self.nb_st1, n_frac=self.nbf_st1, rounding='floor')
            y2 = self.round.crnd(val=y2, signed=True, n_word=self.nb_st1, n_frac=self.nbf_st1, rounding='floor')
            y3 = self.round.crnd(val=y3, signed=True, n_word=self.nb_st1, n_frac=self.nbf_st1, rounding='floor')
            result = [y0, y1, y2, y3]
        return result

    def fft4_radix4(self, x):
        """FFT4-Radix-4"""
        h_result = [0.0 + 1j*0.0] * self.N

        for m in range(int(self.N/4)):
            input_select = [x[m], x[m+4], x[m+8], x[m+12]]
            result_butterfly = self.fft4_radix4_buttefly(input_select)
            for k in range(int(self.N/4)):
                idx = (m * 4) + k
                value = result_butterfly[k] * self.TW16[m * k]
                if self.fxp == 0:
                    h_result[idx] = value
                else:
                    h_result[idx] = self.round.crnd(val=value, signed=True, n_word=self.nb_st2, n_frac=self.nbf_st2, rounding='around')
        return h_result


    def fft4_radix2(self, x):
        """FFT4-Radix-2"""
        b0, b1, b2, b3 = x[0], x[1], x[2], x[3]

        # Stage 1
        v0_real = b0.real + b2.real
        v0_imag = b0.imag + b2.imag
        v0 = complex(v0_real, v0_imag)

        v1_real = b0.real - b2.real
        v1_imag = b0.imag - b2.imag
        v1 = complex(v1_real, v1_imag)

        v2_real = b1.real + b3.real
        v2_imag = b1.imag + b3.imag
        v2 = complex(v2_real, v2_imag)

        v3_real = b1.real - b3.real
        v3_imag = b1.imag - b3.imag
        v3 = complex(v3_real, v3_imag)        
        
        # Twiddle factor correction
        if self.fft_mode == 1:
            v3_fix_real = +v3.imag
            v3_fix_imag = -v3.real
        else:
            v3_fix_real = -v3.imag
            v3_fix_imag = +v3.real
        v3 = complex(v3_fix_real, v3_fix_imag)
        
        # Stage 2
        y0 = v0 + v2
        y1 = v1 + v3
        y2 = v0 - v2
        y3 = v1 - v3
        
        result = [y0, y1, y2, y3]

        # if self.fft_mode == 1:
        #     if self.fxp == 0:
        #         result = [y0, y1, y2, y3]
        #     else:
        #         y0 = self.round.crnd(val=y0, signed=True, n_word=self.nb_out, n_frac=self.nbf_out, rounding='around')
        #         y1 = self.round.crnd(val=y1, signed=True, n_word=self.nb_out, n_frac=self.nbf_out, rounding='around')
        #         y2 = self.round.crnd(val=y2, signed=True, n_word=self.nb_out, n_frac=self.nbf_out, rounding='around')
        #         y3 = self.round.crnd(val=y3, signed=True, n_word=self.nb_out, n_frac=self.nbf_out, rounding='around')
        #         result = [y0, y1, y2, y3]
        # else:
        #     if self.fxp == 0:
        #         y0 = y0 / float(1 << int(self.N/4))
        #         y1 = y1 / float(1 << int(self.N/4))
        #         y2 = y2 / float(1 << int(self.N/4))
        #         y3 = y3 / float(1 << int(self.N/4))
        #         result = [y0, y1, y2, y3]
        #     else:
        #         y0_real = y0.real / self.N
        #         y0_imag = y0.imag / self.N
        #         y0 = complex(y0_real,y0_imag)
                
        #         y1_real = y1.real / self.N
        #         y1_imag = y1.imag / self.N
        #         y1 = complex(y1_real,y1_imag)

        #         y2_real = y2.real / self.N
        #         y2_imag = y2.imag / self.N
        #         y2 = complex(y2_real,y2_imag)

        #         y3_real = y3.real / self.N
        #         y3_imag = y3.imag / self.N
        #         y3 = complex(y3_real,y3_imag)

        #         y0 = self.round.crnd(val=y0, signed=True, n_word=self.nb_out, n_frac=self.nbf_out, rounding='around')
        #         y1 = self.round.crnd(val=y1, signed=True, n_word=self.nb_out, n_frac=self.nbf_out, rounding='around')
        #         y2 = self.round.crnd(val=y2, signed=True, n_word=self.nb_out, n_frac=self.nbf_out, rounding='around')
        #         y3 = self.round.crnd(val=y3, signed=True, n_word=self.nb_out, n_frac=self.nbf_out, rounding='around')

        #         result = [y0, y1, y2, y3]

        return result

    def process(self, x):
        if len(x) != self.N:
            raise ValueError(f"Input size is different to {self.N}.")

        fft4_result = self.fft4_radix4(x)

        # FFT4 (Radix-2)
        X_out      = [0] * self.N
        FFT4_shift = [0] * 4
        FFT4_rnd   = [0] * 4
        
        for k in range(4):
            stage2_input = [fft4_result[k], fft4_result[4+k], fft4_result[8+k], fft4_result[12+k]]
            
            stage2_output = self.fft4_radix2(stage2_input)

            if self.fft_mode == 1:
                FFT4_shift[0] = stage2_output[0]
                FFT4_shift[1] = stage2_output[1]
                FFT4_shift[2] = stage2_output[2]
                FFT4_shift[3] = stage2_output[3]
            else:
                FFT4_shift[0] = stage2_output[0] / self.N
                FFT4_shift[1] = stage2_output[1] / self.N
                FFT4_shift[2] = stage2_output[2] / self.N
                FFT4_shift[3] = stage2_output[3] / self.N

            FFT4_rnd[0] = self.round.crnd(val=FFT4_shift[0], signed=True, n_word=self.nb_out, n_frac=self.nbf_out, rounding='around')
            FFT4_rnd[1] = self.round.crnd(val=FFT4_shift[1], signed=True, n_word=self.nb_out, n_frac=self.nbf_out, rounding='around')
            FFT4_rnd[2] = self.round.crnd(val=FFT4_shift[2], signed=True, n_word=self.nb_out, n_frac=self.nbf_out, rounding='around')
            FFT4_rnd[3] = self.round.crnd(val=FFT4_shift[3], signed=True, n_word=self.nb_out, n_frac=self.nbf_out, rounding='around') 

            X_out[k]      = FFT4_rnd[0]
            X_out[k + 4]  = FFT4_rnd[1]
            X_out[k + 8]  = FFT4_rnd[2]
            X_out[k + 12] = FFT4_rnd[3]

        return X_out
    
import numpy as np


def test_fft16():
    import matplotlib.pyplot as plt

    print("--- FFT16 verification ---")
    
    N = 16
    FXP = 1
    NB_INPUT  = 8
    NBF_INPUT = 6
    NB_OUT  = 8
    NBF_OUT = 3
    rounding = ROUND()

    test_signal_float = 2 * np.random.uniform(-1, 1, N) + 2j * np.random.uniform(-1, 1, N)
    test_signal = rounding.crnd_vec(val_vec = test_signal_float, signed=True,  n_word=NB_INPUT, n_frac=NBF_INPUT, rounding='around')
    test_signal = np.array(test_signal)


    # =========================================================
    # FIG 1: 
    # =========================================================
    time_bins = np.arange(N)
    freq_bins = np.arange(N)
    fig_in, ax_in = plt.subplots(figsize=(10, 5))
    ax_in.set_title('Input Signal: Time Domain (N=16)', fontsize=16)
    
    # Graficamos parte real e imaginaria
    ax_in.stem(time_bins, test_signal.real, 
               linefmt='b-', markerfmt='bo', basefmt='k-', 
               label='Real Part')
    ax_in.stem(time_bins, test_signal.imag, 
               linefmt='r-', markerfmt='rx', basefmt='k-', 
               label='Imaginary Part')
               
    ax_in.set_ylabel('Amplitude', fontsize=12)
    ax_in.set_xlabel('Sample Index (n)', fontsize=12)
    ax_in.set_xticks(time_bins)
    ax_in.legend()
    ax_in.grid(True)

    plt.tight_layout()
    plt.savefig("input_fft16.pdf")
    plt.close(fig_in)

    # =========================================================
    # FIG 2:
    # =========================================================
    fft16_hibrid = FFT16(N=N, fxp=FXP, NB_INPUT=NB_INPUT, NBF_INPUT=NBF_INPUT, fft_mode=1)
    fft16_hibrid_result = fft16_hibrid.process(test_signal)
    
    numpy_result = np.fft.fft(test_signal)
    
    diferencia = np.array(fft16_hibrid_result) - numpy_result
    max_error = np.max(np.abs(diferencia))
    
    print(f"Maximum Absolute Error Detected: {max_error:.2e}")
    
    for i in range(4):
        print(f"Bin {i}:")
        print(f"  NumPy  : {numpy_result[i]:.4f}")
        print(f"  Hibrid : {fft16_hibrid_result[i]:.4f}")

    freq_bins = np.arange(16)
    fig, axs = plt.subplots(2, 1, figsize=(12, 10))
    axs[0].set_title('FFT16 Comparison: NumPy vs. FFT16_fxp', fontsize=16)

    axs[0].stem(freq_bins, np.abs(numpy_result), 
                linefmt='b-', markerfmt='bo', basefmt=' ', 
                label='NumPy (Floating-Point Reference)')

    axs[0].stem(freq_bins, np.abs(fft16_hibrid_result), 
                linefmt='r:', markerfmt='rx', basefmt=' ',
                label='FFT16_fxp')

    axs[0].set_ylabel('Magnitude |X(k)|', fontsize=12)
    axs[0].set_xticks(freq_bins)
    axs[0].legend()
    axs[0].grid(True)

    error_vector = numpy_result - fft16_hibrid_result
    epsilon = 1e-20
    error_magnitude_db = 20 * np.log10(np.abs(error_vector) + epsilon)

    axs[1].set_title('Error Plot (dB)', fontsize=16)
    axs[1].stem(freq_bins, error_magnitude_db, 
                linefmt='g-', markerfmt='go', basefmt=' ')
    axs[1].set_xlabel('Frequency Bin', fontsize=12)
    axs[1].set_ylabel('Error [dB]', fontsize=12)
    axs[1].set_xticks(freq_bins)
    axs[1].grid(True)

    plt.savefig("result_fft16.pdf")
    plt.close()
    
    # =========================================================
    # FIG 3
    # =========================================================
    print("\n--- IFFT16 Verification ---")

    ifft16_hibrid = FFT16(N=N, fxp=FXP, NB_INPUT=NB_OUT, NBF_INPUT=NBF_OUT, fft_mode=0)
    ifft16_hibrid_result = ifft16_hibrid.process(fft16_hibrid_result)

    reconstructed_signal = np.array(ifft16_hibrid_result)
    error_reconstruccion = test_signal - reconstructed_signal
    max_error_recon = np.max(np.abs(error_reconstruccion))
    
    print(f"Maximum absolute error at Reconstruction: {max_error_recon:.2e}")
    
    for i in range(4):
        print(f"Sample {i}:")
        print(f"  Original : {test_signal[i]:.4f}")
        print(f"  IFFT : {reconstructed_signal[i]:.4f}")

    fig_recon, axs_recon = plt.subplots(2, 1, figsize=(12, 10))
    axs_recon[0].set_title('Time Domain Reconstruction: Original vs IFFT Output', fontsize=16)

    axs_recon[0].stem(time_bins, test_signal.real, 
                      linefmt='b-', markerfmt='bo', basefmt='k-', 
                      label='Original (Real)')
    axs_recon[0].stem(time_bins, reconstructed_signal.real, 
                      linefmt='r:', markerfmt='rx', basefmt=' ', 
                      label='IFFT (Real)')
    axs_recon[0].set_ylabel('Amplitude', fontsize=12)
    axs_recon[0].set_xticks(time_bins)
    axs_recon[0].legend()
    axs_recon[0].grid(True)

    epsilon_recon = 1e-20
    error_recon_db = 20 * np.log10(np.abs(error_reconstruccion) + epsilon_recon)

    axs_recon[1].set_title('Reconstruction Error (dB)', fontsize=16)
    axs_recon[1].stem(time_bins, error_recon_db, linefmt='g-', markerfmt='go', basefmt=' ')
    axs_recon[1].set_xlabel('Sample Index (n)', fontsize=12)
    axs_recon[1].set_ylabel('Error [dB]', fontsize=12)
    axs_recon[1].set_xticks(time_bins)
    axs_recon[1].grid(True)

    plt.tight_layout()
    plt.savefig("result_ifft16.pdf")
    plt.close(fig_recon)


if __name__ == "__main__":
    test_fft16()
