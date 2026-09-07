import math
import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

from model_fft4_mul import (
    DATA_MAX,
    DATA_MIN,
    NB_DATA,
    NBF_OUT,
    NBF_TW,
    expected,
    to_signed,
    tw_from_angle,
)

CLK_NS = 10
LATENCY = 3
PIPE_DEPTH = 2
MASK = (1 << NB_DATA) - 1

TW_UNITY = (511, 0)
TW_MINUS_J = (0, -512)
TW_PLUS_J = (0, 511)
TW_MINUS_ONE = (-512, 0)


async def start(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    dut.i_en.value = 1
    dut.i_data_re.value = 0
    dut.i_data_im.value = 0
    dut.i_tw_re.value = 0
    dut.i_tw_im.value = 0
    for _ in range(4):
        await RisingEdge(dut.i_clk)


async def apply(dut, data_re, data_im, tw_re, tw_im):
    dut.i_data_re.value = data_re & MASK
    dut.i_data_im.value = data_im & MASK
    dut.i_tw_re.value = tw_re & MASK
    dut.i_tw_im.value = tw_im & MASK
    for _ in range(LATENCY):
        await RisingEdge(dut.i_clk)
    return (
        to_signed(dut.o_data_re.value, NB_DATA),
        to_signed(dut.o_data_im.value, NB_DATA),
    )


async def check(dut, data_re, data_im, tw_re, tw_im):
    got = await apply(dut, data_re, data_im, tw_re, tw_im)
    exp = expected(data_re, data_im, tw_re, tw_im)
    assert got == exp, (
        f"data=({data_re},{data_im}) tw=({tw_re},{tw_im}): "
        f"expected {exp}, got {got}"
    )
    return got


@cocotb.test()
async def test_multiply_by_unity(dut):
    await start(dut)
    for value in range(-64, 65):
        got = await check(dut, value, -value, *TW_UNITY)
        ideal = value * 511 / (2 ** NBF_TW)
        assert abs(got[0] - ideal) <= 1.0, (
            f"unity twiddle should preserve {value}, got {got[0]}"
        )
    cocotb.log.info("Unity twiddle preserves the data OK")


@cocotb.test()
async def test_multiply_by_minus_j(dut):
    await start(dut)
    for value in range(-100, 101, 5):
        await check(dut, value, value // 2, *TW_MINUS_J)
    cocotb.log.info("-j twiddle OK")


@cocotb.test()
async def test_multiply_by_plus_j(dut):
    await start(dut)
    for value in range(-100, 101, 5):
        await check(dut, value, -value // 3, *TW_PLUS_J)
    cocotb.log.info("+j twiddle OK")


@cocotb.test()
async def test_multiply_by_minus_one(dut):
    await start(dut)
    for value in range(-120, 121, 3):
        got = await check(dut, value, -value, *TW_MINUS_ONE)
        assert abs(got[0] + value) <= 1.0, (
            f"-1 twiddle should negate {value}, got {got[0]}"
        )
    cocotb.log.info("-1 twiddle negates the data OK")


@cocotb.test()
async def test_zero_data_and_zero_twiddle(dut):
    await start(dut)
    got = await check(dut, 0, 0, 511, 0)
    assert got == (0, 0), f"zero data must give zero output, got {got}"
    for value in [-512, -1, 1, 511]:
        got = await check(dut, value, value, 0, 0)
        assert got == (0, 0), f"zero twiddle must give zero output, got {got}"
    cocotb.log.info("Zero data and zero twiddle OK")


@cocotb.test()
async def test_fft16_twiddle_set(dut):
    await start(dut)
    for inverse in (0, 1):
        for k in range(16):
            tw_re, tw_im = tw_from_angle(k, 16, inverse)
            for value in range(-96, 97, 8):
                await check(dut, value, -value // 2, tw_re, tw_im)
        cocotb.log.info(f"All 16 FFT16 twiddles for inverse={inverse} OK")


@cocotb.test()
async def test_random_vectors(dut):
    await start(dut)
    rng = random.Random(21)
    for _ in range(6000):
        await check(
            dut,
            rng.randint(DATA_MIN, DATA_MAX),
            rng.randint(DATA_MIN, DATA_MAX),
            rng.randint(DATA_MIN, DATA_MAX),
            rng.randint(DATA_MIN, DATA_MAX),
        )
    cocotb.log.info("6000 random vectors match the bit-exact model OK")


@cocotb.test()
async def test_extreme_operands_saturate(dut):
    await start(dut)
    extremes = [DATA_MIN, DATA_MIN + 1, -1, 0, 1, DATA_MAX - 1, DATA_MAX]
    saturated = 0
    for data_re in extremes:
        for data_im in extremes:
            for tw_re in extremes:
                for tw_im in extremes:
                    got = await check(dut, data_re, data_im, tw_re, tw_im)
                    assert DATA_MIN <= got[0] <= DATA_MAX
                    assert DATA_MIN <= got[1] <= DATA_MAX
                    if got[0] in (DATA_MIN, DATA_MAX):
                        saturated += 1
    cocotb.log.info(
        f"{len(extremes) ** 4} extreme combinations, {saturated} saturated OK"
    )


@cocotb.test()
async def test_unit_gain_twiddles(dut):
    await start(dut)
    rng = random.Random(24)
    for inverse in (0, 1):
        for _ in range(400):
            data_re = rng.randint(-180, 180)
            data_im = rng.randint(-180, 180)
            k = rng.randint(0, 15)
            tw_re, tw_im = tw_from_angle(k, 16, inverse)
            got = await check(dut, data_re, data_im, tw_re, tw_im)
            if DATA_MIN in got or DATA_MAX in got:
                continue
            mag_in = math.hypot(data_re, data_im)
            mag_out = math.hypot(got[0], got[1])
            assert abs(mag_out - mag_in) <= 2.0 + 0.01 * mag_in, (
                f"unit-magnitude twiddle {k} must preserve the vector length: "
                f"|in|={mag_in:.3f} |out|={mag_out:.3f}"
            )
        cocotb.log.info(f"Twiddle multiply has unit gain for inverse={inverse} OK")


@cocotb.test()
async def test_rotation_direction(dut):
    await start(dut)
    for inverse in (0, 1):
        for k in [1, 2, 3, 4, 5, 6, 7]:
            tw_re, tw_im = tw_from_angle(k, 16, inverse)
            got = await check(dut, 400, 0, tw_re, tw_im)
            angle = math.atan2(got[1], got[0])
            sign = 1.0 if inverse else -1.0
            want = sign * 2.0 * math.pi * k / 16.0
            diff = (angle - want + math.pi) % (2 * math.pi) - math.pi
            assert abs(diff) < 0.05, (
                f"twiddle {k}: expected rotation {want:.4f} rad, "
                f"measured {angle:.4f} rad"
            )
        cocotb.log.info(f"Rotation follows the twiddle sign for inverse={inverse} OK")


@cocotb.test()
async def test_pipeline_latency(dut):
    await start(dut)
    baseline = await apply(dut, 0, 0, 511, 0)
    assert baseline == (0, 0)
    dut.i_data_re.value = 256
    dut.i_data_im.value = 0
    dut.i_tw_re.value = 511
    dut.i_tw_im.value = 0
    for step in range(PIPE_DEPTH):
        await RisingEdge(dut.i_clk)
        held = to_signed(dut.o_data_re.value, NB_DATA)
        assert held == 0, (
            f"output changed after {step + 1} clocks, expected {PIPE_DEPTH} "
            f"clocks of latency, got {held}"
        )
    await RisingEdge(dut.i_clk)
    assert to_signed(dut.o_data_re.value, NB_DATA) != 0, (
        "output must update once the pipeline has drained"
    )
    cocotb.log.info(f"Pipeline latency of {PIPE_DEPTH} clocks confirmed OK")


@cocotb.test()
async def test_enable_gating(dut):
    await start(dut)
    settled = await check(dut, 300, -200, *tw_from_angle(3, 16, 0))
    dut.i_en.value = 0
    dut.i_data_re.value = 511
    dut.i_data_im.value = 511
    dut.i_tw_re.value = 511
    dut.i_tw_im.value = 511
    for _ in range(20):
        await RisingEdge(dut.i_clk)
        got = (
            to_signed(dut.o_data_re.value, NB_DATA),
            to_signed(dut.o_data_im.value, NB_DATA),
        )
        assert got == settled, (
            f"the output must hold while i_en is low: {settled} became {got}"
        )
    dut.i_en.value = 1
    await RisingEdge(dut.i_clk)
    cocotb.log.info("Registers hold their value while i_en is low OK")


@cocotb.test()
async def test_streaming_back_to_back(dut):
    await start(dut)
    rng = random.Random(23)
    vectors = [
        (
            rng.randint(-256, 255),
            rng.randint(-256, 255),
            *tw_from_angle(rng.randint(0, 15), 16, 0),
        )
        for _ in range(200)
    ]
    outputs = []
    for data_re, data_im, tw_re, tw_im in vectors:
        dut.i_data_re.value = data_re & MASK
        dut.i_data_im.value = data_im & MASK
        dut.i_tw_re.value = tw_re & MASK
        dut.i_tw_im.value = tw_im & MASK
        await RisingEdge(dut.i_clk)
        outputs.append(
            (
                to_signed(dut.o_data_re.value, NB_DATA),
                to_signed(dut.o_data_im.value, NB_DATA),
            )
        )
    for _ in range(PIPE_DEPTH):
        await RisingEdge(dut.i_clk)
        outputs.append(
            (
                to_signed(dut.o_data_re.value, NB_DATA),
                to_signed(dut.o_data_im.value, NB_DATA),
            )
        )
    for idx, vector in enumerate(vectors):
        exp = expected(*vector)
        got = outputs[idx + PIPE_DEPTH]
        assert got == exp, f"streaming sample {idx}: expected {exp}, got {got}"
    cocotb.log.info(f"{len(vectors)} back-to-back samples pipeline correctly OK")
