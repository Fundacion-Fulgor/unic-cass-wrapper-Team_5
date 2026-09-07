import cocotb
import numpy as np
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from fft16 import FFT16


def golden_stage2(model, stage1):
    out = [0] * 16
    for k in range(4):
        pair = [stage1[k], stage1[4 + k], stage1[8 + k], stage1[12 + k]]
        values = model.fft4_radix2(pair)
        out[k] = values[0]
        out[k + 4] = values[1]
        out[k + 8] = values[2]
        out[k + 12] = values[3]
    return out

# =====================================================
# Helpers
# =====================================================


def float_to_int(val, frac_bits):
    return int(round(val * (2**frac_bits)))


def int_to_float(val, frac_bits):
    return val / (2**frac_bits)


# =====================================================
# DUT reset
# =====================================================


async def full_reset(dut, inverse_val):
    """Assert reset for 8 cycles to flush all pipeline state."""
    dut.i_en.value = 0
    dut.i_rstn.value = 0
    dut.i_inverse.value = inverse_val
    dut.i_valid.value = 0
    dut.i_tx_ready.value = 1
    dut.i_data_re.value = 0
    dut.i_data_im.value = 0
    for _ in range(8):
        await RisingEdge(dut.i_clk)
    dut.i_rstn.value = 1
    await RisingEdge(dut.i_clk)
    dut.i_en.value = 1
    await RisingEdge(dut.i_clk)


# =====================================================
# Capture coroutines
# =====================================================


async def capture_stage1(dut, N, NBF_STAGE1, results, timeout=5000):
    cycles = 0
    while len(results) < N and cycles < timeout:
        await RisingEdge(dut.i_clk)
        cycles += 1
        if dut.fft4_valid.value == 1:
            re_ports = [
                dut.fft4_data0_re,
                dut.fft4_data1_re,
                dut.fft4_data2_re,
                dut.fft4_data3_re,
            ]
            im_ports = [
                dut.fft4_data0_im,
                dut.fft4_data1_im,
                dut.fft4_data2_im,
                dut.fft4_data3_im,
            ]
            for p_re, p_im in zip(re_ports, im_ports):
                results.append(
                    complex(
                        int_to_float(p_re.value.to_signed(), NBF_STAGE1),
                        int_to_float(p_im.value.to_signed(), NBF_STAGE1),
                    )
                )
    assert len(results) == N, f"Stage 1 capture timeout: got {len(results)} of {N}."


async def capture_mdc(
    dut, N, NBF_STAGE1, NBF_STAGE2, mdc_results, stage2_results, inverse, timeout=5000
):
    """
    Captures both the raw MDC butterfly output and the final clip_round output.
    For FFT  (inverse=0) reads rnd_mdc*  (NBF_OUT = NB_DATA-5 = 3).
    For IFFT (inverse=1) reads rnd_ifft* (NBF_OUT = NB_DATA-2 = 6).
    """
    cycles = 0
    while len(mdc_results) < N and cycles < timeout:
        await RisingEdge(dut.i_clk)
        cycles += 1
        if dut.mdc_ffx_valid.value == 1:
            re_mdc = [
                dut.mdc_ff0_data0_re,
                dut.mdc_ff0_data1_re,
                dut.mdc_ff1_data0_re,
                dut.mdc_ff1_data1_re,
                dut.mdc_ff2_data0_re,
                dut.mdc_ff2_data1_re,
                dut.mdc_ff3_data0_re,
                dut.mdc_ff3_data1_re,
            ]
            im_mdc = [
                dut.mdc_ff0_data0_im,
                dut.mdc_ff0_data1_im,
                dut.mdc_ff1_data0_im,
                dut.mdc_ff1_data1_im,
                dut.mdc_ff2_data0_im,
                dut.mdc_ff2_data1_im,
                dut.mdc_ff3_data0_im,
                dut.mdc_ff3_data1_im,
            ]
            if inverse == 0:
                re_out = [
                    dut.rnd_mdc0_x0_re,
                    dut.rnd_mdc0_x1_re,
                    dut.rnd_mdc1_x0_re,
                    dut.rnd_mdc1_x1_re,
                    dut.rnd_mdc2_x0_re,
                    dut.rnd_mdc2_x1_re,
                    dut.rnd_mdc3_x0_re,
                    dut.rnd_mdc3_x1_re,
                ]
                im_out = [
                    dut.rnd_mdc0_x0_im,
                    dut.rnd_mdc0_x1_im,
                    dut.rnd_mdc1_x0_im,
                    dut.rnd_mdc1_x1_im,
                    dut.rnd_mdc2_x0_im,
                    dut.rnd_mdc2_x1_im,
                    dut.rnd_mdc3_x0_im,
                    dut.rnd_mdc3_x1_im,
                ]
            else:
                re_out = [
                    dut.rnd_ifft0_x0_re,
                    dut.rnd_ifft0_x1_re,
                    dut.rnd_ifft1_x0_re,
                    dut.rnd_ifft1_x1_re,
                    dut.rnd_ifft2_x0_re,
                    dut.rnd_ifft2_x1_re,
                    dut.rnd_ifft3_x0_re,
                    dut.rnd_ifft3_x1_re,
                ]
                im_out = [
                    dut.rnd_ifft0_x0_im,
                    dut.rnd_ifft0_x1_im,
                    dut.rnd_ifft1_x0_im,
                    dut.rnd_ifft1_x1_im,
                    dut.rnd_ifft2_x0_im,
                    dut.rnd_ifft2_x1_im,
                    dut.rnd_ifft3_x0_im,
                    dut.rnd_ifft3_x1_im,
                ]
            for i in range(8):
                mdc_results.append(
                    complex(
                        int_to_float(re_mdc[i].value.to_signed(), NBF_STAGE1),
                        int_to_float(im_mdc[i].value.to_signed(), NBF_STAGE1),
                    )
                )
                stage2_results.append(
                    complex(
                        int_to_float(re_out[i].value.to_signed(), NBF_STAGE2),
                        int_to_float(im_out[i].value.to_signed(), NBF_STAGE2),
                    )
                )
    assert len(mdc_results) == N, f"MDC capture timeout: got {len(mdc_results)} of {N}."


async def tx_serializer_model(
    dut, NB_DATA, collected, expected_count, timeout=50000, nbf=3
):
    BUSY_CYCLES = 1 + 2 * NB_DATA
    dut.i_tx_ready.value = 1
    cycles = 0
    while len(collected) < expected_count and cycles < timeout:
        await RisingEdge(dut.i_clk)
        cycles += 1
        if dut.o_valid.value == 1 and dut.i_tx_ready.value == 1:
            re = int_to_float(dut.o_data_re.value.to_signed(), nbf)
            im = int_to_float(dut.o_data_im.value.to_signed(), nbf)
            collected.append(complex(re, im))
            dut.i_tx_ready.value = 0
            for _ in range(BUSY_CYCLES):
                await RisingEdge(dut.i_clk)
            dut.i_tx_ready.value = 1
    assert len(collected) == expected_count, (
        f"Buffer capture timeout: got {len(collected)} of {expected_count}."
    )


# =====================================================
# Reorder helper
# =====================================================

MDC_MAP = [0, 8, 1, 9, 2, 10, 3, 11, 4, 12, 5, 13, 6, 14, 7, 15]


def reorder(seq, n, mapping):
    out = [0j] * n
    for i, v in enumerate(seq):
        out[mapping[i]] = v
    return out


# =====================================================
# Core test logic (shared by both tests)
# =====================================================


async def run_fft_test(dut, inverse):
    """
    Runs a full stage-by-stage test in either FFT or IFFT mode.
      inverse=0 -> FFT:  input Q(8,6), output Q(8,3)
      inverse=1 -> IFFT: input Q(8,3), output Q(8,6)
    """
    NB_DATA = 8
    N = 16

    if inverse == 0:
        NBF_DATA = 6
        NBF_STAGE1 = 6
        NBF_STAGE2 = 3
        fft_mode = 1
        mode_str = "FFT"
    else:
        NBF_DATA = 3
        NBF_STAGE1 = 3
        NBF_STAGE2 = 6
        fft_mode = 0
        mode_str = "IFFT"

    fft_model = FFT16(
        N=N, fxp=1, NB_INPUT=NB_DATA, NBF_INPUT=NBF_DATA, fft_mode=fft_mode
    )

    # Reset DUT cleanly before each test
    await full_reset(dut, inverse)

    cocotb.log.info("=" * 80)
    cocotb.log.info(f"Starting FFT16 {mode_str} Stage-by-Stage Verification")
    cocotb.log.info("=" * 80)

    # Build quantised input vector
    input_float = 2 * np.random.uniform(-1, 1, N) + 2j * np.random.uniform(-1, 1, N)
    input_q = [
        fft_model.round.crnd(x, True, NB_DATA, NBF_DATA, "around") for x in input_float
    ]
    expected_fft4rdx4 = fft_model.fft4_radix4(input_q)
    expected_fft4rdx2 = golden_stage2(fft_model, expected_fft4rdx4)
    expected_out = fft_model.process(input_q)

    # Launch captures BEFORE injection
    rtl_stage1 = []
    rtl_mdc = []
    rtl_stage2 = []
    collected_buffer = []

    task_stage1 = cocotb.start_soon(capture_stage1(dut, N, NBF_STAGE1, rtl_stage1))

    task_mdc = cocotb.start_soon(
        capture_mdc(dut, N, NBF_STAGE1, NBF_STAGE2, rtl_mdc, rtl_stage2, inverse)
    )

    task_buffer = cocotb.start_soon(
        tx_serializer_model(dut, NB_DATA, collected_buffer, N, nbf=NBF_STAGE2)
    )

    # Gapped injection: 1 valid + 15 idle per sample
    for i in range(N):
        dut.i_valid.value = 1
        dut.i_data_re.value = float_to_int(input_q[i].real, NBF_DATA)
        dut.i_data_im.value = float_to_int(input_q[i].imag, NBF_DATA)
        await RisingEdge(dut.i_clk)
        dut.i_valid.value = 0
        if i < N - 1:
            for _ in range(15):
                await RisingEdge(dut.i_clk)

    await task_stage1
    await task_mdc
    await task_buffer

    # Reorder
    rtl_mdc_ord = reorder(rtl_mdc, N, MDC_MAP)
    rtl_output_ord = reorder(rtl_stage2, N, MDC_MAP)
    buffer_ord = reorder(collected_buffer, N, MDC_MAP)

    tol = 1e-9

    # --- Stage 1 ---
    cocotb.log.info("\n" + "=" * 80)
    cocotb.log.info(f"{mode_str} STAGE 1 (Radix-4 Butterfly)")
    cocotb.log.info("=" * 80)
    cocotb.log.info(f"{'Idx':<5} | {'RTL':<32} | {'Python':<32} | Δre / Δim")
    cocotb.log.info("-" * 80)
    for idx in range(N):
        rv = rtl_stage1[idx]
        pv = expected_fft4rdx4[idx]
        dre, dim = abs(rv.real - pv.real), abs(rv.imag - pv.imag)
        cocotb.log.info(
            f"{idx:<5} | {rv.real:+.6f} {rv.imag:+.6f}j | "
            f"{pv.real:+.6f} {pv.imag:+.6f}j | {dre:.2e} / {dim:.2e}"
        )
        assert dre < tol and dim < tol, (
            f"[Stage1] mismatch idx={idx}: RTL={rv}  Py={pv}"
        )
    cocotb.log.info("Stage 1 PASSED.")

    # --- MDC Stage ---
    cocotb.log.info("\n" + "=" * 80)
    cocotb.log.info(f"{mode_str} MDC STAGE (Radix-2 pre-clip)")
    cocotb.log.info("=" * 80)
    cocotb.log.info(f"{'Idx':<5} | {'RTL':<32} | {'Python':<32} | Δre / Δim")
    cocotb.log.info("-" * 80)
    for idx in range(N):
        rv = rtl_mdc_ord[idx]
        pv = expected_fft4rdx2[idx]
        dre, dim = abs(rv.real - pv.real), abs(rv.imag - pv.imag)
        cocotb.log.info(
            f"{idx:<5} | {rv.real:+.6f} {rv.imag:+.6f}j | "
            f"{pv.real:+.6f} {pv.imag:+.6f}j | {dre:.2e} / {dim:.2e}"
        )
        assert dre < tol and dim < tol, f"[MDC] mismatch idx={idx}: RTL={rv}  Py={pv}"
    cocotb.log.info("MDC Stage PASSED.")

    # --- Final Output (clip_round) ---
    cocotb.log.info("\n" + "=" * 80)
    cocotb.log.info(
        f"{mode_str} FINAL OUTPUT (clip_round, {'rnd_mdc*' if inverse == 0 else 'rnd_ifft*'})"
    )
    cocotb.log.info("=" * 80)
    cocotb.log.info(f"{'Idx':<5} | {'RTL':<32} | {'Python':<32} | Δre / Δim")
    cocotb.log.info("-" * 80)
    for idx in range(N):
        rv = rtl_output_ord[idx]
        pv = expected_out[idx]
        dre, dim = abs(rv.real - pv.real), abs(rv.imag - pv.imag)
        cocotb.log.info(
            f"{idx:<5} | {rv.real:+.6f} {rv.imag:+.6f}j | "
            f"{pv.real:+.6f} {pv.imag:+.6f}j | {dre:.2e} / {dim:.2e}"
        )
        assert dre < tol and dim < tol, f"[Final] mismatch idx={idx}: RTL={rv}  Py={pv}"
    cocotb.log.info("Final Output PASSED.")

    # --- Buffer Output (tx_serializer) ---
    cocotb.log.info("\n" + "=" * 80)
    cocotb.log.info(f"{mode_str} BUFFER OUTPUT (tx_serializer)")
    cocotb.log.info("=" * 80)
    cocotb.log.info(f"{'Idx':<5} | {'Buffer':<32} | {'Python':<32} | Δre / Δim")
    cocotb.log.info("-" * 80)
    for idx in range(N):
        rv = buffer_ord[idx]
        pv = expected_out[idx]
        dre, dim = abs(rv.real - pv.real), abs(rv.imag - pv.imag)
        cocotb.log.info(
            f"{idx:<5} | {rv.real:+.6f} {rv.imag:+.6f}j | "
            f"{pv.real:+.6f} {pv.imag:+.6f}j | {dre:.2e} / {dim:.2e}"
        )
        assert dre < tol and dim < tol, (
            f"[Buffer] mismatch idx={idx}: RTL={rv}  Py={pv}"
        )
    cocotb.log.info("Buffer Output PASSED.")
    cocotb.log.info(f"{'=' * 80}")
    cocotb.log.info(f"ALL {mode_str} STAGES PASSED.")
    cocotb.log.info(f"{'=' * 80}")


# =====================================================
# Individual test entries
# =====================================================


@cocotb.test()
async def test_fft16_fft(dut):
    """Forward FFT: input Q(8,6), output Q(8,3), i_inverse=0."""
    clock = Clock(dut.i_clk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    await run_fft_test(dut, inverse=0)


@cocotb.test()
async def test_fft16_ifft(dut):
    """Inverse FFT: input Q(8,3), output Q(8,6), i_inverse=1.
    The /N=16 normalisation is encoded in clip_round via NBF_INP=7 (=NBF_MDC+4).
    No explicit >>>4 shift is needed or correct in the RTL."""
    clock = Clock(dut.i_clk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    await run_fft_test(dut, inverse=1)


NB_DATA = 8
N = 16


def make_model(inverse):
    nbf_in = 3 if inverse else 6
    return FFT16(N=N, fxp=1, NB_INPUT=NB_DATA, NBF_INPUT=nbf_in, fft_mode=0 if inverse else 1)


def quantise(model, values, nbf_in):
    return [model.round.crnd(v, True, NB_DATA, nbf_in, "around") for v in values]


async def drive_block(dut, input_q, nbf_in, gap=15):
    for idx, value in enumerate(input_q):
        dut.i_valid.value = 1
        dut.i_data_re.value = float_to_int(value.real, nbf_in)
        dut.i_data_im.value = float_to_int(value.imag, nbf_in)
        await RisingEdge(dut.i_clk)
        dut.i_valid.value = 0
        if idx < len(input_q) - 1:
            for _ in range(gap):
                await RisingEdge(dut.i_clk)


async def run_block(dut, input_q, nbf_in, nbf_out):
    collected = []
    task = cocotb.start_soon(
        tx_serializer_model(dut, NB_DATA, collected, N, nbf=nbf_out)
    )
    await drive_block(dut, input_q, nbf_in)
    await task
    return reorder(collected, N, MDC_MAP)


def compare(got, expected, context=""):
    for idx in range(N):
        dre = abs(got[idx].real - expected[idx].real)
        dim = abs(got[idx].imag - expected[idx].imag)
        assert dre < 1e-9 and dim < 1e-9, (
            f"{context}bin {idx}: RTL={got[idx]} model={expected[idx]}"
        )


def formats(inverse):
    return (3, 6) if inverse else (6, 3)


async def process_random_blocks(dut, inverse, n_blocks, seed):
    nbf_in, nbf_out = formats(inverse)
    model = make_model(inverse)
    np.random.seed(seed)
    for block in range(n_blocks):
        raw = 2 * np.random.uniform(-1, 1, N) + 2j * np.random.uniform(-1, 1, N)
        input_q = quantise(model, raw, nbf_in)
        expected = model.process(input_q)
        got = await run_block(dut, input_q, nbf_in, nbf_out)
        compare(got, expected, f"block {block}: ")
    return n_blocks


@cocotb.test()
async def test_fft_consecutive_blocks(dut):
    cocotb.start_soon(Clock(dut.i_clk, 10, unit="ns").start())
    await full_reset(dut, 0)
    count = await process_random_blocks(dut, inverse=0, n_blocks=6, seed=201)
    cocotb.log.info(f"{count} consecutive FFT blocks without reset OK")


@cocotb.test()
async def test_ifft_consecutive_blocks(dut):
    cocotb.start_soon(Clock(dut.i_clk, 10, unit="ns").start())
    await full_reset(dut, 1)
    count = await process_random_blocks(dut, inverse=1, n_blocks=6, seed=202)
    cocotb.log.info(f"{count} consecutive IFFT blocks without reset OK")


@cocotb.test()
async def test_zero_input(dut):
    cocotb.start_soon(Clock(dut.i_clk, 10, unit="ns").start())
    for inverse in (0, 1):
        await full_reset(dut, inverse)
        nbf_in, nbf_out = formats(inverse)
        got = await run_block(dut, [complex(0, 0)] * N, nbf_in, nbf_out)
        for idx, value in enumerate(got):
            assert value == complex(0, 0), (
                f"inverse={inverse} bin {idx}: expected 0, got {value}"
            )
        cocotb.log.info(f"inverse={inverse}: zero input gives zero output OK")


@cocotb.test()
async def test_dc_input(dut):
    cocotb.start_soon(Clock(dut.i_clk, 10, unit="ns").start())
    await full_reset(dut, 0)
    model = make_model(0)
    amplitude = 1.0
    input_q = quantise(model, [complex(amplitude, 0)] * N, 6)
    expected = model.process(input_q)
    got = await run_block(dut, input_q, 6, 3)
    compare(got, expected)
    non_zero = [idx for idx, v in enumerate(got) if v != 0]
    assert non_zero == [0], (
        f"a DC input must excite only bin 0, non-zero bins: {non_zero}"
    )
    cocotb.log.info(f"DC input concentrates in bin 0 with value {got[0]} OK")


@cocotb.test()
async def test_impulse_input(dut):
    cocotb.start_soon(Clock(dut.i_clk, 10, unit="ns").start())
    await full_reset(dut, 0)
    model = make_model(0)
    samples = [complex(0, 0)] * N
    samples[0] = complex(1.0, 0)
    input_q = quantise(model, samples, 6)
    expected = model.process(input_q)
    got = await run_block(dut, input_q, 6, 3)
    compare(got, expected)
    for idx in range(1, N):
        assert got[idx] == got[0], (
            f"an impulse must give a flat spectrum, bin {idx}={got[idx]} "
            f"vs bin 0={got[0]}"
        )
    cocotb.log.info(f"Impulse input gives a flat spectrum of {got[0]} OK")


@cocotb.test()
async def test_single_tone_bins(dut):
    cocotb.start_soon(Clock(dut.i_clk, 10, unit="ns").start())
    model = make_model(0)
    for k in [1, 2, 3, 4, 5, 6, 7]:
        await full_reset(dut, 0)
        samples = [
            complex(
                0.5 * float(np.cos(2 * np.pi * k * n / N)),
                0.5 * float(np.sin(2 * np.pi * k * n / N)),
            )
            for n in range(N)
        ]
        input_q = quantise(model, samples, 6)
        expected = model.process(input_q)
        got = await run_block(dut, input_q, 6, 3)
        compare(got, expected, f"tone k={k}: ")
        peak = max(range(N), key=lambda i: abs(got[i]))
        assert peak == k, f"tone at bin {k} peaked at bin {peak} instead"
        cocotb.log.info(f"  tone k={k} peaks at bin {peak}, matches the model")
    cocotb.log.info("Single tone inputs match the golden model bit for bit OK")


@cocotb.test()
async def test_mode_switch_between_blocks(dut):
    cocotb.start_soon(Clock(dut.i_clk, 10, unit="ns").start())
    for seed, inverse in enumerate([0, 1, 0, 1, 1, 0], start=210):
        await full_reset(dut, inverse)
        await process_random_blocks(dut, inverse=inverse, n_blocks=2, seed=seed)
    cocotb.log.info("Alternating FFT and IFFT blocks with a reset in between OK")


@cocotb.test()
async def test_full_scale_input(dut):
    cocotb.start_soon(Clock(dut.i_clk, 10, unit="ns").start())
    await full_reset(dut, 0)
    model = make_model(0)
    extremes = [-2.0, 127 / 64.0, -1.0, 1.0]
    samples = [
        complex(extremes[i % len(extremes)], extremes[(i * 3) % len(extremes)])
        for i in range(N)
    ]
    input_q = quantise(model, samples, 6)
    expected = model.process(input_q)
    got = await run_block(dut, input_q, 6, 3)
    compare(got, expected)
    cocotb.log.info("Full-scale input matches the saturating model OK")


@cocotb.test()
async def test_output_sample_count(dut):
    cocotb.start_soon(Clock(dut.i_clk, 10, unit="ns").start())
    await full_reset(dut, 0)
    model = make_model(0)
    np.random.seed(220)
    for block in range(4):
        raw = 2 * np.random.uniform(-1, 1, N) + 2j * np.random.uniform(-1, 1, N)
        input_q = quantise(model, raw, 6)
        collected = []
        task = cocotb.start_soon(
            tx_serializer_model(dut, NB_DATA, collected, N, nbf=3)
        )
        await drive_block(dut, input_q, 6)
        await task
        assert len(collected) == N, (
            f"block {block} produced {len(collected)} samples instead of {N}"
        )
    cocotb.log.info("Exactly 16 output samples per input block OK")


@cocotb.test()
async def test_clk_en_gating(dut):
    cocotb.start_soon(Clock(dut.i_clk, 10, unit="ns").start())
    await full_reset(dut, 0)
    model = make_model(0)

    dut.i_en.value = 0
    dut.i_valid.value = 1
    dut.i_data_re.value = 127
    dut.i_data_im.value = -128
    for _ in range(40):
        await RisingEdge(dut.i_clk)
    dut.i_valid.value = 0
    dut.i_data_re.value = 0
    dut.i_data_im.value = 0
    dut.i_en.value = 1
    await RisingEdge(dut.i_clk)

    np.random.seed(221)
    raw = 2 * np.random.uniform(-1, 1, N) + 2j * np.random.uniform(-1, 1, N)
    input_q = quantise(model, raw, 6)
    expected = model.process(input_q)
    got = await run_block(dut, input_q, 6, 3)
    compare(got, expected)
    cocotb.log.info("Samples driven while i_en was low are ignored OK")


@cocotb.test()
async def test_reset_between_blocks(dut):
    cocotb.start_soon(Clock(dut.i_clk, 10, unit="ns").start())
    model = make_model(0)
    np.random.seed(222)
    for block in range(4):
        await full_reset(dut, 0)
        raw = 2 * np.random.uniform(-1, 1, N) + 2j * np.random.uniform(-1, 1, N)
        input_q = quantise(model, raw, 6)
        expected = model.process(input_q)
        got = await run_block(dut, input_q, 6, 3)
        compare(got, expected, f"block {block}: ")
    cocotb.log.info("A reset before every block also works OK")
