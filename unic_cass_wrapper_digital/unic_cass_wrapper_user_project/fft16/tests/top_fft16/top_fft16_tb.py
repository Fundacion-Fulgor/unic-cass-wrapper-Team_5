import cocotb
import numpy as np
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

CLK_NS = 20
SPI_HALF_NS = 50
NB_DATA = 8
N = 16
TIMEOUT = 2000

SPI_RW_WRITE = 0
SPI_RW_READ = 1

ADDR_STATUS_FLAGS = 0x00
ADDR_ERROR_FLAGS = 0x01
ADDR_CNT_INPUTS = 0x02
ADDR_CNT_OUTPUTS = 0x03
ADDR_LAST_OUT_RE = 0x04
ADDR_LAST_OUT_IM = 0x05
ADDR_MID_DATA_RE = 0x06
ADDR_SYS_CONFIG = 0x10

CFG_DISABLE = 0b000
CFG_ENABLE = 0b001  # fft_enable=1, inverse=0
CFG_ENABLE_IFFT = 0b011  # fft_enable=1, inverse=1  (bit1 = i_inverse)
CFG_SRESET = 0b100

# Cycles to wait after enabling clk_en before injecting real data.
# fft16_shift_r4 and fft16_shift_r2 have no reset port — they only gate on
# i_en.  Residual valid pulses drain in at most a few dozen cycles.
PIPELINE_DRAIN_CYCLES = 64

# Fixed-point formats
NBF_FFT_IN = 6  # Q(8,6) — FFT  input  / IFFT output
NBF_FFT_OUT = 3  # Q(8,3) — FFT  output / IFFT input
MDC_MAP = [0, 8, 1, 9, 2, 10, 3, 11, 4, 12, 5, 13, 6, 14, 7, 15]


def to_signed_8(val):
    val = val & 0xFF
    return val - 256 if val > 127 else val


# ─────────────────────────────────────────────────────────────────
# Infrastructure helpers
# ─────────────────────────────────────────────────────────────────


async def reset_dut(dut):
    dut.i_rstn.value = 0
    dut.i_data.value = 0
    dut.i_spi_ss_n.value = 1
    dut.i_spi_sclk.value = 0
    dut.i_spi_mosi.value = 0
    for _ in range(4):
        await RisingEdge(dut.i_clk)
    dut.i_rstn.value = 1
    await RisingEdge(dut.i_clk)


async def full_reset(dut):
    await reset_dut(dut)
    await spi_write(dut, ADDR_SYS_CONFIG, CFG_SRESET)
    for _ in range(8):
        await RisingEdge(dut.i_clk)
    await spi_write(dut, ADDR_SYS_CONFIG, CFG_DISABLE)
    for _ in range(4):
        await RisingEdge(dut.i_clk)


async def enable_fft_and_drain(dut):
    await spi_write(dut, ADDR_SYS_CONFIG, CFG_ENABLE)
    for _ in range(PIPELINE_DRAIN_CYCLES):
        await RisingEdge(dut.i_clk)


async def enable_ifft_and_drain(dut):
    await spi_write(dut, ADDR_SYS_CONFIG, CFG_ENABLE_IFFT)
    for _ in range(PIPELINE_DRAIN_CYCLES):
        await RisingEdge(dut.i_clk)


async def soft_reset_between_blocks(dut, cfg_enable=CFG_ENABLE):
    await spi_write(dut, ADDR_SYS_CONFIG, CFG_SRESET)
    for _ in range(8):
        await RisingEdge(dut.i_clk)
    await spi_write(dut, ADDR_SYS_CONFIG, cfg_enable)
    for _ in range(PIPELINE_DRAIN_CYCLES):
        await RisingEdge(dut.i_clk)


async def spi_transfer(dut, rw, addr, wdata=0x00):
    frame = ((rw & 1) << 15) | ((addr & 0x7F) << 8) | (wdata & 0xFF)
    dut.i_spi_ss_n.value = 0
    dut.i_spi_sclk.value = 0
    dut.i_spi_mosi.value = 0
    await Timer(SPI_HALF_NS, unit="ns")
    miso_byte = 0
    for i in range(16):
        dut.i_spi_mosi.value = (frame >> (15 - i)) & 1
        await Timer(SPI_HALF_NS, unit="ns")
        dut.i_spi_sclk.value = 1
        await Timer(SPI_HALF_NS, unit="ns")
        dut.i_spi_sclk.value = 0
        await Timer(SPI_HALF_NS, unit="ns")
        if 7 <= i <= 14:
            miso_byte = (miso_byte << 1) | int(dut.o_spi_miso.value)
    dut.i_spi_ss_n.value = 1
    await Timer(SPI_HALF_NS, unit="ns")
    for _ in range(8):
        await RisingEdge(dut.i_clk)
    return miso_byte


async def spi_write(dut, addr, data):
    await spi_transfer(dut, SPI_RW_WRITE, addr, data)


async def spi_read(dut, addr):
    return await spi_transfer(dut, SPI_RW_READ, addr)


async def drive_stream(dut, pairs):
    dut.i_data.value = 0
    await RisingEdge(dut.i_clk)
    dut.i_data.value = 1
    await RisingEdge(dut.i_clk)
    for re_val, im_val in pairs:
        word = ((re_val & 0xFF) << 8) | (im_val & 0xFF)
        for i in range(16):
            dut.i_data.value = (word >> (15 - i)) & 1
            await RisingEdge(dut.i_clk)
    dut.i_data.value = 0


async def capture_block(dut, n_samples):
    results = []
    for idx in range(n_samples):
        if idx == 0:
            cycles = 0
            while cycles < TIMEOUT:
                await RisingEdge(dut.i_clk)
                cycles += 1
                if int(dut.o_data.value) == 1:
                    break
            else:
                assert False, "Timeout: start bit never detected on o_data"
        else:
            await RisingEdge(dut.i_clk)
            await RisingEdge(dut.i_clk)

        word = 0
        for _ in range(16):
            await RisingEdge(dut.i_clk)
            word = (word << 1) | int(dut.o_data.value)

        results.append((to_signed_8(word >> 8), to_signed_8(word & 0xFF)))

    return results


# ─────────────────────────────────────────────────────────────────
# Shared roundtrip helper
# ─────────────────────────────────────────────────────────────────


async def run_roundtrip(dut, inverse, seed=42):
    """
    Drives one block through the FFT or IFFT, captures the output and
    compares it against the FFT16 Python fixed-point model.

    inverse=0: FFT  — input Q(8,6), output Q(8,3)
    inverse=1: IFFT — input Q(8,3), output Q(8,6)
    """
    from fft16 import FFT16

    if inverse == 0:
        nbf_in = NBF_FFT_IN
        nbf_out = NBF_FFT_OUT
        fft_mode = 1
        mode_str = "FFT"
    else:
        nbf_in = NBF_FFT_OUT  # IFFT input is frequency-domain Q(8,3)
        nbf_out = NBF_FFT_IN  # IFFT output is time-domain Q(8,6)
        fft_mode = 0
        mode_str = "IFFT"

    fft_model = FFT16(N=N, fxp=1, NB_INPUT=NB_DATA, NBF_INPUT=nbf_in, fft_mode=fft_mode)

    np.random.seed(seed)
    input_float = 2 * np.random.uniform(-1, 1, N) + 2j * np.random.uniform(-1, 1, N)

    input_q = [
        fft_model.round.crnd(x, True, NB_DATA, nbf_in, "around") for x in input_float
    ]

    expected_out = fft_model.process(input_q)

    def fxp_to_int8(c, nbf):
        re = max(-128, min(127, int(round(c.real * (2**nbf)))))
        im = max(-128, min(127, int(round(c.imag * (2**nbf)))))
        return re, im

    def int8_to_float(val, nbf):
        return val / (2**nbf)

    samples_int = [fxp_to_int8(x, nbf_in) for x in input_q]

    send_task = cocotb.start_soon(drive_stream(dut, samples_int))
    received = await capture_block(dut, N)
    await send_task

    cocotb.log.info(f"  Captured {len(received)} {mode_str} output samples")
    cocotb.log.info("\n" + "=" * 90)
    cocotb.log.info(
        f"{mode_str} ROUNDTRIP RESULTS  (nbf_in={nbf_in} nbf_out={nbf_out})"
    )
    cocotb.log.info("=" * 90)
    cocotb.log.info(
        f"{'Phys':<6} {'Bin':<5} | "
        f"{'RTL Re':>10} {'RTL Im':>10} | "
        f"{'Exp Re':>10} {'Exp Im':>10} | "
        f"{'Delta Re':>10} {'Delta Im':>10}"
    )
    cocotb.log.info("-" * 90)

    TOL = 1e-9
    all_ok = True
    for phys_idx in range(N):
        bin_idx = MDC_MAP[phys_idx]
        got_re_int, got_im_int = received[phys_idx]
        got_re = int8_to_float(got_re_int, nbf_out)
        got_im = int8_to_float(got_im_int, nbf_out)
        exp_re = float(expected_out[bin_idx].real)
        exp_im = float(expected_out[bin_idx].imag)
        diff_re = abs(got_re - exp_re)
        diff_im = abs(got_im - exp_im)
        match = diff_re < TOL and diff_im < TOL
        if not match:
            all_ok = False
        cocotb.log.info(
            f"  [{phys_idx:<3}] bin={bin_idx:<3} | "
            f"{got_re:+.6f} {got_im:+.6f}j | "
            f"{exp_re:+.6f} {exp_im:+.6f}j | "
            f"{diff_re:.2e} {diff_im:.2e} "
            f"{'OK' if match else 'MISMATCH'}"
        )

    assert all_ok, f"One or more {mode_str} output samples do not match the model"
    cocotb.log.info("=" * 90)
    return received


# ─────────────────────────────────────────────────────────────────
# FFT Tests
# ─────────────────────────────────────────────────────────────────


@cocotb.test()
async def test_fft_disabled_no_output(dut):
    """
    With sys_config=0b000 (fft_enable=0), rx_serializer still counts inputs
    but fft16 is gated: o_data stays 0 and cnt_outputs=0.
    """
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await full_reset(dut)
    cocotb.log.info("--- test_fft_disabled_no_output ---")

    samples = [(i * 3, i * 2) for i in range(N)]
    await drive_stream(dut, samples)

    for _ in range(200):
        await RisingEdge(dut.i_clk)
        assert int(dut.o_data.value) == 0, "o_data must remain 0 when FFT is disabled"
    cocotb.log.info("  o_data stayed 0 with FFT disabled  OK")

    for _ in range(10):
        await RisingEdge(dut.i_clk)

    cnt_in = await spi_read(dut, ADDR_CNT_INPUTS)
    cnt_out = await spi_read(dut, ADDR_CNT_OUTPUTS)
    assert cnt_in == N, f"cnt_inputs: expected {N}, got {cnt_in}"
    assert cnt_out == 0, f"cnt_outputs: expected 0, got {cnt_out}"
    cocotb.log.info(f"  cnt_inputs={cnt_in}  cnt_outputs={cnt_out}  OK")
    cocotb.log.info("test_fft_disabled_no_output PASSED.")


@cocotb.test()
async def test_enable_counters_and_status(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await full_reset(dut)
    cocotb.log.info("--- test_enable_counters_and_status ---")

    await enable_fft_and_drain(dut)

    samples = [(10 * (i % 4 + 1), -5 * (i % 4 + 1)) for i in range(N)]
    send_task = cocotb.start_soon(drive_stream(dut, samples))
    received = await capture_block(dut, N)
    await send_task

    non_zero = [(re, im) for re, im in received if re != 0 or im != 0]
    assert len(non_zero) > 0, "All output samples are (0,0)"
    cocotb.log.info(f"  {len(non_zero)}/{N} non-zero output samples  OK")

    for _ in range(20):
        await RisingEdge(dut.i_clk)

    cnt_in = await spi_read(dut, ADDR_CNT_INPUTS)
    cnt_out = await spi_read(dut, ADDR_CNT_OUTPUTS)
    assert cnt_in == N, f"cnt_inputs: expected {N}, got {cnt_in}"
    assert cnt_out == N, f"cnt_outputs: expected {N}, got {cnt_out}"
    cocotb.log.info(f"  cnt_inputs={cnt_in}  cnt_outputs={cnt_out}  OK")

    status = await spi_read(dut, ADDR_STATUS_FLAGS)
    assert (status >> 2) & 1 == 1, (
        f"tx_ready should be 1 when idle, status=0x{status:02X}"
    )
    assert (status >> 3) & 1 == 0, (
        f"fft_inverse should be 0 in FFT mode, status=0x{status:02X}"
    )
    cocotb.log.info(f"  status_flags=0x{status:02X}  OK")

    last_re = to_signed_8(await spi_read(dut, ADDR_LAST_OUT_RE))
    last_im = to_signed_8(await spi_read(dut, ADDR_LAST_OUT_IM))
    exp_re, exp_im = received[-1]
    assert last_re == exp_re, f"last_out_re: expected {exp_re}, got {last_re}"
    assert last_im == exp_im, f"last_out_im: expected {exp_im}, got {last_im}"
    cocotb.log.info(f"  last_out: re={last_re} im={last_im}  OK")
    cocotb.log.info("test_enable_counters_and_status PASSED.")


@cocotb.test()
async def test_zero_input(dut):
    """FFT of all-zero input must be all-zero with no clipping."""
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await full_reset(dut)
    cocotb.log.info("--- test_zero_input ---")

    await enable_fft_and_drain(dut)

    send_task = cocotb.start_soon(drive_stream(dut, [(0, 0)] * N))
    received = await capture_block(dut, N)
    await send_task

    for i, (re, im) in enumerate(received):
        assert re == 0 and im == 0, f"Sample {i}: expected (0,0), got ({re},{im})"
    cocotb.log.info(f"  All {N} output samples are (0,0)  OK")

    for _ in range(10):
        await RisingEdge(dut.i_clk)
    err = await spi_read(dut, ADDR_ERROR_FLAGS)
    assert (err & 0x01) == 0, (
        f"error_flags[0] should be 0 for zero input, got 0x{err:02X}"
    )
    cocotb.log.info(f"  error_flags=0x{err:02X} (no clipping)  OK")
    cocotb.log.info("test_zero_input PASSED.")


@cocotb.test()
async def test_soft_reset(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await full_reset(dut)
    cocotb.log.info("--- test_soft_reset ---")

    await enable_fft_and_drain(dut)

    send_task = cocotb.start_soon(
        drive_stream(dut, [(i + 1, -(i + 1)) for i in range(N)])
    )
    await capture_block(dut, N)
    await send_task

    for _ in range(10):
        await RisingEdge(dut.i_clk)

    cnt_in = await spi_read(dut, ADDR_CNT_INPUTS)
    cnt_out = await spi_read(dut, ADDR_CNT_OUTPUTS)
    assert cnt_in == N, f"Pre-reset cnt_inputs: expected {N}, got {cnt_in}"
    assert cnt_out == N, f"Pre-reset cnt_outputs: expected {N}, got {cnt_out}"
    cocotb.log.info(f"  Pre-reset: cnt_inputs={cnt_in} cnt_outputs={cnt_out}  OK")

    await spi_write(dut, ADDR_SYS_CONFIG, CFG_SRESET)
    for _ in range(10):
        await RisingEdge(dut.i_clk)
    await spi_write(dut, ADDR_SYS_CONFIG, CFG_ENABLE)
    for _ in range(PIPELINE_DRAIN_CYCLES):
        await RisingEdge(dut.i_clk)

    cnt_in = await spi_read(dut, ADDR_CNT_INPUTS)
    cnt_out = await spi_read(dut, ADDR_CNT_OUTPUTS)
    assert cnt_in == 0, f"Post-reset cnt_inputs: expected 0, got {cnt_in}"
    assert cnt_out == 0, f"Post-reset cnt_outputs: expected 0, got {cnt_out}"
    cocotb.log.info(f"  Post-reset: cnt_inputs={cnt_in} cnt_outputs={cnt_out}  OK")

    send_task = cocotb.start_soon(drive_stream(dut, [(0, 0)] * N))
    received = await capture_block(dut, N)
    await send_task
    assert len(received) == N, (
        f"Post-reset block: expected {N} samples, got {len(received)}"
    )
    cocotb.log.info(f"  Post-reset block: {N} outputs received  OK")
    cocotb.log.info("test_soft_reset PASSED.")


@cocotb.test()
async def test_spi_last_out_tracking(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await full_reset(dut)
    cocotb.log.info("--- test_spi_last_out_tracking ---")

    await enable_fft_and_drain(dut)

    for block_idx in range(2):
        samples = [
            ((block_idx + 1) * (i % 8 + 1), -(block_idx + 1) * (i % 8 + 1))
            for i in range(N)
        ]
        send_task = cocotb.start_soon(drive_stream(dut, samples))
        received = await capture_block(dut, N)
        await send_task

        for _ in range(20):
            await RisingEdge(dut.i_clk)

        non_zero = [(re, im) for re, im in received if re != 0 or im != 0]
        assert len(non_zero) > 0, f"Block {block_idx}: all outputs are (0,0)"
        cocotb.log.info(
            f"  Block {block_idx}: {len(non_zero)}/{N} non-zero samples  OK"
        )

        last_re = to_signed_8(await spi_read(dut, ADDR_LAST_OUT_RE))
        last_im = to_signed_8(await spi_read(dut, ADDR_LAST_OUT_IM))
        exp_re, exp_im = received[-1]
        assert last_re == exp_re, (
            f"Block {block_idx} last_out_re: expected {exp_re}, got {last_re}"
        )
        assert last_im == exp_im, (
            f"Block {block_idx} last_out_im: expected {exp_im}, got {last_im}"
        )
        cocotb.log.info(f"  Block {block_idx} last_out: re={last_re} im={last_im}  OK")

        if block_idx < 1:
            await soft_reset_between_blocks(dut, CFG_ENABLE)

    cnt_in = await spi_read(dut, ADDR_CNT_INPUTS)
    cnt_out = await spi_read(dut, ADDR_CNT_OUTPUTS)
    assert cnt_in == N, f"cnt_inputs after last block: expected {N}, got {cnt_in}"
    assert cnt_out == N, f"cnt_outputs after last block: expected {N}, got {cnt_out}"
    cocotb.log.info(f"  Final counters: cnt_inputs={cnt_in} cnt_outputs={cnt_out}  OK")
    cocotb.log.info("test_spi_last_out_tracking PASSED.")


@cocotb.test()
async def test_dc_input_energy(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await full_reset(dut)
    cocotb.log.info("--- test_dc_input_energy ---")

    await enable_fft_and_drain(dut)

    A = 4
    send_task = cocotb.start_soon(drive_stream(dut, [(A, 0)] * N))
    received = await capture_block(dut, N)
    await send_task

    non_zero = [
        (i, re, im) for i, (re, im) in enumerate(received) if re != 0 or im != 0
    ]
    cocotb.log.info(f"  Non-zero outputs: {non_zero}")

    assert len(non_zero) == 1, (
        f"DC input should produce exactly 1 non-zero bin, got {len(non_zero)}: {non_zero}"
    )
    bin0_phys, bin0_re, bin0_im = non_zero[0]
    cocotb.log.info(
        f"  Bin 0 at physical index {bin0_phys}: re={bin0_re} im={bin0_im}  OK"
    )

    for _ in range(10):
        await RisingEdge(dut.i_clk)
    err = await spi_read(dut, ADDR_ERROR_FLAGS)
    assert (err & 0x01) == 0, (
        f"No clipping expected for DC A={A}, error_flags=0x{err:02X}"
    )
    cocotb.log.info(f"  error_flags=0x{err:02X} (no clipping)  OK")
    cocotb.log.info("test_dc_input_energy PASSED.")


@cocotb.test()
async def test_fft_mathematical_roundtrip(dut):
    """Full end-to-end FFT: input Q(8,6), output Q(8,3)."""
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await full_reset(dut)
    cocotb.log.info("--- test_fft_mathematical_roundtrip ---")
    await enable_fft_and_drain(dut)
    await run_roundtrip(dut, inverse=0, seed=42)
    cocotb.log.info("test_fft_mathematical_roundtrip PASSED.")


# ─────────────────────────────────────────────────────────────────
# IFFT Tests
# ─────────────────────────────────────────────────────────────────


@cocotb.test()
async def test_ifft_status_flag(dut):
    """
    After enabling with CFG_ENABLE_IFFT, status_flags[3] (fft_inverse)
    must read back as 1.
    """
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await full_reset(dut)
    cocotb.log.info("--- test_ifft_status_flag ---")

    await enable_ifft_and_drain(dut)

    status = await spi_read(dut, ADDR_STATUS_FLAGS)
    assert (status >> 3) & 1 == 1, (
        f"fft_inverse flag should be 1 in IFFT mode, status=0x{status:02X}"
    )
    cocotb.log.info(f"  status_flags=0x{status:02X} (fft_inverse=1)  OK")
    cocotb.log.info("test_ifft_status_flag PASSED.")


@cocotb.test()
async def test_ifft_zero_input(dut):
    """IFFT of all-zero frequency-domain input must be all-zero time-domain output."""
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await full_reset(dut)
    cocotb.log.info("--- test_ifft_zero_input ---")

    await enable_ifft_and_drain(dut)

    send_task = cocotb.start_soon(drive_stream(dut, [(0, 0)] * N))
    received = await capture_block(dut, N)
    await send_task

    for i, (re, im) in enumerate(received):
        assert re == 0 and im == 0, (
            f"IFFT zero-input: sample {i} expected (0,0), got ({re},{im})"
        )
    cocotb.log.info(f"  All {N} IFFT output samples are (0,0)  OK")

    for _ in range(10):
        await RisingEdge(dut.i_clk)
    err = await spi_read(dut, ADDR_ERROR_FLAGS)
    assert (err & 0x01) == 0, (
        f"No clipping expected for zero IFFT input, error_flags=0x{err:02X}"
    )
    cocotb.log.info(f"  error_flags=0x{err:02X} (no clipping)  OK")
    cocotb.log.info("test_ifft_zero_input PASSED.")


@cocotb.test()
async def test_ifft_dc_bin(dut):
    """
    IFFT of a single non-zero DC bin (bin 0 only) produces a constant
    real time-domain sequence.  All samples must have the same re value
    and zero imaginary part.
    The serial output is in MDC order, so physical index 0 corresponds to
    frequency bin MDC_MAP[0]=0.  We send A in bin 0 and zero in all others,
    then after IFFT + 1/N scaling every time-domain sample should be A/N.
    """
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await full_reset(dut)
    cocotb.log.info("--- test_ifft_dc_bin ---")

    await enable_ifft_and_drain(dut)

    # Build freq-domain input: A in bin 0, zeros elsewhere.
    # The MDC_MAP tells us which physical serial position maps to which bin.
    # To put energy in bin 0 we need physical position MDC_MAP.index(0)=0.
    A = 32  # Q(8,3): 32 * 2^-3 = 4.0
    freq_samples = [(0, 0)] * N
    phys_bin0 = MDC_MAP.index(0)
    freq_samples[phys_bin0] = (A, 0)

    send_task = cocotb.start_soon(drive_stream(dut, freq_samples))
    received = await capture_block(dut, N)
    await send_task

    # A is an integer in Q(8,3): float = A / 2^NBF_FFT_OUT = 32/8 = 4.0
    # After IFFT + 1/N scaling: float = 4.0 / N = 0.25
    # Output is Q(8,6): integer = 0.25 * 2^NBF_FFT_IN = 16
    expected_int = round(A * (2**NBF_FFT_IN) / (N * (2**NBF_FFT_OUT)))
    cocotb.log.info(f"  Expected time-domain integer value per sample: {expected_int}")

    for i, (re, im) in enumerate(received):
        assert re == expected_int, (
            f"IFFT DC bin: sample {i} re expected {expected_int}, got {re}"
        )
        assert im == 0, f"IFFT DC bin: sample {i} im expected 0, got {im}"
    cocotb.log.info(f"  All {N} time-domain samples re={expected_int} im=0  OK")
    cocotb.log.info("test_ifft_dc_bin PASSED.")


@cocotb.test()
async def test_ifft_counters(dut):
    """IFFT mode: cnt_inputs and cnt_outputs increment correctly."""
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await full_reset(dut)
    cocotb.log.info("--- test_ifft_counters ---")

    await enable_ifft_and_drain(dut)

    samples = [(i % 16, -(i % 8)) for i in range(N)]
    send_task = cocotb.start_soon(drive_stream(dut, samples))
    received = await capture_block(dut, N)
    await send_task

    for _ in range(20):
        await RisingEdge(dut.i_clk)

    cnt_in = await spi_read(dut, ADDR_CNT_INPUTS)
    cnt_out = await spi_read(dut, ADDR_CNT_OUTPUTS)
    assert cnt_in == N, f"IFFT cnt_inputs: expected {N}, got {cnt_in}"
    assert cnt_out == N, f"IFFT cnt_outputs: expected {N}, got {cnt_out}"
    cocotb.log.info(f"  cnt_inputs={cnt_in}  cnt_outputs={cnt_out}  OK")

    last_re = to_signed_8(await spi_read(dut, ADDR_LAST_OUT_RE))
    last_im = to_signed_8(await spi_read(dut, ADDR_LAST_OUT_IM))
    exp_re, exp_im = received[-1]
    assert last_re == exp_re, f"IFFT last_out_re: expected {exp_re}, got {last_re}"
    assert last_im == exp_im, f"IFFT last_out_im: expected {exp_im}, got {last_im}"
    cocotb.log.info(f"  last_out: re={last_re} im={last_im}  OK")
    cocotb.log.info("test_ifft_counters PASSED.")


@cocotb.test()
async def test_ifft_mathematical_roundtrip(dut):
    """Full end-to-end IFFT: input Q(8,3), output Q(8,6)."""
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await full_reset(dut)
    cocotb.log.info("--- test_ifft_mathematical_roundtrip ---")
    await enable_ifft_and_drain(dut)
    await run_roundtrip(dut, inverse=1, seed=99)
    cocotb.log.info("test_ifft_mathematical_roundtrip PASSED.")


@cocotb.test()
async def test_fft_ifft_mode_switch(dut):
    """
    Verify that switching FFT → IFFT → FFT via soft-reset produces correct
    results in each mode.  This exercises the i_inverse path through the full
    reset/drain sequence.
    """
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await full_reset(dut)
    cocotb.log.info("--- test_fft_ifft_mode_switch ---")

    # Block 1: FFT
    await enable_fft_and_drain(dut)
    cocotb.log.info("  [1/3] FFT block")
    await run_roundtrip(dut, inverse=0, seed=7)

    # Switch to IFFT
    await soft_reset_between_blocks(dut, CFG_ENABLE_IFFT)

    # Block 2: IFFT
    cocotb.log.info("  [2/3] IFFT block")
    await run_roundtrip(dut, inverse=1, seed=13)

    # Switch back to FFT
    await soft_reset_between_blocks(dut, CFG_ENABLE)

    # Block 3: FFT again
    cocotb.log.info("  [3/3] FFT block again")
    await run_roundtrip(dut, inverse=0, seed=21)

    cocotb.log.info("test_fft_ifft_mode_switch PASSED.")


async def enable_and_drain(dut, inverse):
    if inverse:
        await enable_ifft_and_drain(dut)
    else:
        await enable_fft_and_drain(dut)


async def run_many_blocks(dut, inverse, n_blocks, first_seed):
    for block in range(n_blocks):
        cocotb.log.info(f"  block {block}")
        await run_roundtrip(dut, inverse=inverse, seed=first_seed + block)


@cocotb.test()
async def test_fft_back_to_back_blocks(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await full_reset(dut)
    cocotb.log.info("--- test_fft_back_to_back_blocks ---")

    await enable_fft_and_drain(dut)
    await run_many_blocks(dut, inverse=0, n_blocks=5, first_seed=300)

    for _ in range(20):
        await RisingEdge(dut.i_clk)
    cnt_in = await spi_read(dut, ADDR_CNT_INPUTS)
    cnt_out = await spi_read(dut, ADDR_CNT_OUTPUTS)
    assert cnt_in == (5 * N) % 256, f"cnt_inputs: expected {(5 * N) % 256}, got {cnt_in}"
    assert cnt_out == (5 * N) % 256, (
        f"cnt_outputs: expected {(5 * N) % 256}, got {cnt_out}"
    )
    cocotb.log.info(f"  cnt_inputs={cnt_in} cnt_outputs={cnt_out}  OK")
    cocotb.log.info("test_fft_back_to_back_blocks PASSED.")


@cocotb.test()
async def test_ifft_back_to_back_blocks(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await full_reset(dut)
    cocotb.log.info("--- test_ifft_back_to_back_blocks ---")

    await enable_ifft_and_drain(dut)
    await run_many_blocks(dut, inverse=1, n_blocks=5, first_seed=400)
    cocotb.log.info("test_ifft_back_to_back_blocks PASSED.")


@cocotb.test()
async def test_dc_repeated_without_reset(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await full_reset(dut)
    cocotb.log.info("--- test_dc_repeated_without_reset ---")

    await enable_fft_and_drain(dut)
    A = 4
    for block in range(6):
        send_task = cocotb.start_soon(drive_stream(dut, [(A, 0)] * N))
        received = await capture_block(dut, N)
        await send_task
        non_zero = [(i, re, im) for i, (re, im) in enumerate(received) if re or im]
        assert len(non_zero) == 1, (
            f"block {block}: DC input must give exactly one non-zero bin, "
            f"got {non_zero}"
        )
        assert non_zero[0][0] == 0, (
            f"block {block}: the non-zero bin must be at physical index 0"
        )
        cocotb.log.info(f"  block {block}: bin 0 = {non_zero[0][1:]}  OK")
    cocotb.log.info("test_dc_repeated_without_reset PASSED.")


@cocotb.test()
async def test_impulse_response(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await full_reset(dut)
    cocotb.log.info("--- test_impulse_response ---")

    await enable_fft_and_drain(dut)
    samples = [(0, 0)] * N
    samples[0] = (64, 0)
    send_task = cocotb.start_soon(drive_stream(dut, samples))
    received = await capture_block(dut, N)
    await send_task

    first = received[0]
    for idx, sample in enumerate(received):
        assert sample == first, (
            f"an impulse must give a flat spectrum, index {idx}={sample} "
            f"vs index 0={first}"
        )
    assert first != (0, 0), "the flat spectrum must be non-zero"
    cocotb.log.info(f"  All 16 bins equal {first}  OK")
    cocotb.log.info("test_impulse_response PASSED.")


@cocotb.test()
async def test_single_tone_peaks(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await full_reset(dut)
    cocotb.log.info("--- test_single_tone_peaks ---")

    await enable_fft_and_drain(dut)
    for k in [1, 2, 4, 6]:
        samples = []
        for n in range(N):
            angle = 2 * np.pi * k * n / N
            samples.append(
                (
                    int(round(np.cos(angle) * 63)),
                    int(round(np.sin(angle) * 63)),
                )
            )
        send_task = cocotb.start_soon(drive_stream(dut, samples))
        received = await capture_block(dut, N)
        await send_task

        magnitudes = [0.0] * N
        for phys_idx in range(N):
            re, im = received[phys_idx]
            magnitudes[MDC_MAP[phys_idx]] = (re * re + im * im) ** 0.5
        peak = max(range(N), key=lambda i: magnitudes[i])
        assert peak == k, (
            f"tone at bin {k} peaked at bin {peak}, magnitudes={magnitudes}"
        )
        for idx in range(N):
            if idx == k:
                continue
            assert magnitudes[idx] <= 3.0, (
                f"tone k={k}: leakage of {magnitudes[idx]} into bin {idx}"
            )
        cocotb.log.info(f"  tone k={k} peaks at bin {peak}  OK")
    cocotb.log.info("test_single_tone_peaks PASSED.")


@cocotb.test()
async def test_counters_wrap(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await full_reset(dut)
    cocotb.log.info("--- test_counters_wrap ---")

    await enable_fft_and_drain(dut)
    n_blocks = 17
    for block in range(n_blocks):
        send_task = cocotb.start_soon(drive_stream(dut, [(block + 1, -block) for _ in range(N)]))
        received = await capture_block(dut, N)
        await send_task
        assert len(received) == N, (
            f"block {block} produced {len(received)} samples instead of {N}"
        )

    for _ in range(20):
        await RisingEdge(dut.i_clk)
    expected = (n_blocks * N) % 256
    cnt_in = await spi_read(dut, ADDR_CNT_INPUTS)
    cnt_out = await spi_read(dut, ADDR_CNT_OUTPUTS)
    assert cnt_in == expected, f"cnt_inputs: expected {expected}, got {cnt_in}"
    assert cnt_out == expected, f"cnt_outputs: expected {expected}, got {cnt_out}"
    cocotb.log.info(f"  After {n_blocks} blocks: cnt={cnt_in} (wrapped)  OK")
    cocotb.log.info("test_counters_wrap PASSED.")


@cocotb.test()
async def test_clipping_sets_error_flag(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await full_reset(dut)
    cocotb.log.info("--- test_clipping_sets_error_flag ---")

    await enable_fft_and_drain(dut)
    err = await spi_read(dut, ADDR_ERROR_FLAGS)
    assert (err & 0x01) == 0, f"error_flags must start clear, got 0x{err:02X}"

    send_task = cocotb.start_soon(drive_stream(dut, [(127, 127)] * N))
    received = await capture_block(dut, N)
    await send_task

    for _ in range(20):
        await RisingEdge(dut.i_clk)
    err = await spi_read(dut, ADDR_ERROR_FLAGS)
    clipped = any(re in (127, -128) or im in (127, -128) for re, im in received)
    assert (err & 0x01) == (1 if clipped else 0), (
        f"error_flags[0]=0x{err:02X} does not match the observed clipping "
        f"{clipped} in {received}"
    )
    cocotb.log.info(f"  error_flags=0x{err:02X} clipped={clipped}  OK")
    cocotb.log.info("test_clipping_sets_error_flag PASSED.")


@cocotb.test()
async def test_error_flag_cleared_by_soft_reset(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await full_reset(dut)
    cocotb.log.info("--- test_error_flag_cleared_by_soft_reset ---")

    await enable_fft_and_drain(dut)
    send_task = cocotb.start_soon(drive_stream(dut, [(127, 127)] * N))
    await capture_block(dut, N)
    await send_task
    for _ in range(20):
        await RisingEdge(dut.i_clk)

    await soft_reset_between_blocks(dut, CFG_ENABLE)
    err = await spi_read(dut, ADDR_ERROR_FLAGS)
    assert (err & 0x01) == 0, (
        f"a soft reset must clear error_flags, got 0x{err:02X}"
    )
    cocotb.log.info(f"  error_flags=0x{err:02X} after soft reset  OK")
    cocotb.log.info("test_error_flag_cleared_by_soft_reset PASSED.")


@cocotb.test()
async def test_status_flags_bits(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await full_reset(dut)
    cocotb.log.info("--- test_status_flags_bits ---")

    status = await spi_read(dut, ADDR_STATUS_FLAGS)
    assert (status >> 3) & 1 == 0, "fft_inverse must be 0 after reset"
    assert status >> 4 == 0, f"status_flags[7:4] must be zero, got 0x{status:02X}"

    await enable_ifft_and_drain(dut)
    status = await spi_read(dut, ADDR_STATUS_FLAGS)
    assert (status >> 3) & 1 == 1, "fft_inverse must be 1 in IFFT mode"
    assert (status >> 2) & 1 == 1, "tx_ready must be 1 while idle"
    assert status >> 4 == 0, f"status_flags[7:4] must be zero, got 0x{status:02X}"

    await soft_reset_between_blocks(dut, CFG_ENABLE)
    status = await spi_read(dut, ADDR_STATUS_FLAGS)
    assert (status >> 3) & 1 == 0, "fft_inverse must be 0 back in FFT mode"
    cocotb.log.info(f"  status_flags tracks the configuration  OK")
    cocotb.log.info("test_status_flags_bits PASSED.")


@cocotb.test()
async def test_all_sys_config_values(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await full_reset(dut)
    cocotb.log.info("--- test_all_sys_config_values ---")

    for value in range(8):
        await spi_write(dut, ADDR_SYS_CONFIG, value)
        for _ in range(8):
            await RisingEdge(dut.i_clk)
        got = await spi_read(dut, ADDR_SYS_CONFIG)
        if value & 0b100:
            assert got == value or got == 0, (
                f"sys_config {value:#05b} read back as {got:#05b}"
            )
        else:
            assert got == value, (
                f"sys_config {value:#05b} read back as {got:#05b}"
            )
        cocotb.log.info(f"  sys_config={value:#05b} -> {got:#05b}  OK")
    await spi_write(dut, ADDR_SYS_CONFIG, CFG_DISABLE)
    cocotb.log.info("test_all_sys_config_values PASSED.")


@cocotb.test()
async def test_unmapped_registers_read_zero(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await full_reset(dut)
    cocotb.log.info("--- test_unmapped_registers_read_zero ---")

    for addr in [0x07, 0x08, 0x0F, 0x11, 0x3F, 0x7F]:
        got = await spi_read(dut, addr)
        assert got == 0x00, (
            f"unmapped address 0x{addr:02X} must read 0x00, got 0x{got:02X}"
        )
        cocotb.log.info(f"  addr 0x{addr:02X} -> 0x{got:02X}  OK")
    cocotb.log.info("test_unmapped_registers_read_zero PASSED.")


@cocotb.test()
async def test_mid_data_probe(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await full_reset(dut)
    cocotb.log.info("--- test_mid_data_probe ---")

    await enable_fft_and_drain(dut)
    samples = [(i * 4 - 32, -(i * 4 - 32)) for i in range(N)]
    send_task = cocotb.start_soon(drive_stream(dut, samples))
    await capture_block(dut, N)
    await send_task
    for _ in range(20):
        await RisingEdge(dut.i_clk)

    mid = to_signed_8(await spi_read(dut, ADDR_MID_DATA_RE))
    expected = [re for re, _ in samples]
    assert mid in expected, (
        f"mid_data_re={mid} is not one of the injected real values {expected}"
    )
    cocotb.log.info(f"  mid_data_re={mid}  OK")
    cocotb.log.info("test_mid_data_probe PASSED.")


@cocotb.test()
async def test_disable_midstream_stops_output(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await full_reset(dut)
    cocotb.log.info("--- test_disable_midstream_stops_output ---")

    await enable_fft_and_drain(dut)
    await spi_write(dut, ADDR_SYS_CONFIG, CFG_DISABLE)
    for _ in range(10):
        await RisingEdge(dut.i_clk)

    await drive_stream(dut, [(20, -20)] * N)
    for _ in range(300):
        await RisingEdge(dut.i_clk)
        assert int(dut.o_data.value) == 0, (
            "no output may be produced while the FFT core is disabled"
        )

    await soft_reset_between_blocks(dut, CFG_ENABLE)
    send_task = cocotb.start_soon(drive_stream(dut, [(0, 0)] * N))
    received = await capture_block(dut, N)
    await send_task
    assert len(received) == N, "the core must resume after being re-enabled"
    cocotb.log.info("test_disable_midstream_stops_output PASSED.")


@cocotb.test()
async def test_hard_reset_between_blocks(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    cocotb.log.info("--- test_hard_reset_between_blocks ---")

    for block in range(3):
        await full_reset(dut)
        await enable_fft_and_drain(dut)
        await run_roundtrip(dut, inverse=0, seed=500 + block)
        cocotb.log.info(f"  block {block} after a hard reset  OK")
    cocotb.log.info("test_hard_reset_between_blocks PASSED.")


@cocotb.test()
async def test_long_mixed_mode_session(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await full_reset(dut)
    cocotb.log.info("--- test_long_mixed_mode_session ---")

    schedule = [0, 0, 1, 1, 0, 1, 0, 0]
    current = None
    for idx, inverse in enumerate(schedule):
        if current != inverse:
            if current is None:
                await enable_and_drain(dut, inverse)
            else:
                await soft_reset_between_blocks(
                    dut, CFG_ENABLE_IFFT if inverse else CFG_ENABLE
                )
            current = inverse
        await run_roundtrip(dut, inverse=inverse, seed=600 + idx)
        cocotb.log.info(f"  block {idx} ({'IFFT' if inverse else 'FFT'})  OK")
    cocotb.log.info("test_long_mixed_mode_session PASSED.")
