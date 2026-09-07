import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

from model_fft4 import FFT4_Reference
from model_fft4_radix4 import NB_STAGE, NB_TW, process_block, to_signed

CLK_NS = 10
N = 16
NB_INPUT = 8
LATENCY = 6

IN_MIN = -(1 << (NB_INPUT - 1))
IN_MAX = (1 << (NB_INPUT - 1)) - 1
MASK = (1 << NB_INPUT) - 1

NBF_FFT = 6
NBF_IFFT = 3


class Recorder:
    def __init__(self, dut):
        self.dut = dut
        self.captured = []
        self.running = True

    def start(self):
        self.task = cocotb.start_soon(self._run())
        return self

    async def _run(self):
        while self.running:
            await RisingEdge(self.dut.i_clk)
            if self.dut.o_valid.value == 1:
                self.captured.append(
                    [
                        complex(
                            to_signed(self.dut.o_data0_re.value, NB_TW),
                            to_signed(self.dut.o_data0_im.value, NB_TW),
                        ),
                        complex(
                            to_signed(self.dut.o_data1_re.value, NB_TW),
                            to_signed(self.dut.o_data1_im.value, NB_TW),
                        ),
                        complex(
                            to_signed(self.dut.o_data2_re.value, NB_TW),
                            to_signed(self.dut.o_data2_im.value, NB_TW),
                        ),
                        complex(
                            to_signed(self.dut.o_data3_re.value, NB_TW),
                            to_signed(self.dut.o_data3_im.value, NB_TW),
                        ),
                    ]
                )

    async def stop(self, drain=LATENCY + 4):
        for _ in range(drain):
            await RisingEdge(self.dut.i_clk)
        self.running = False
        await RisingEdge(self.dut.i_clk)
        return self.captured


async def reset_dut(dut, inverse=0):
    dut.i_rstn.value = 0
    dut.i_en.value = 0
    dut.i_valid.value = 0
    dut.i_inverse.value = inverse
    for k in range(4):
        getattr(dut, f"i_data{k}_re").value = 0
        getattr(dut, f"i_data{k}_im").value = 0
    for _ in range(4):
        await RisingEdge(dut.i_clk)
    dut.i_rstn.value = 1
    await RisingEdge(dut.i_clk)
    dut.i_en.value = 1
    await RisingEdge(dut.i_clk)


async def start(dut, inverse=0):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await reset_dut(dut, inverse)


async def push_group(dut, group, gap=0):
    for k in range(4):
        getattr(dut, f"i_data{k}_re").value = int(group[k].real) & MASK
        getattr(dut, f"i_data{k}_im").value = int(group[k].imag) & MASK
    dut.i_valid.value = 1
    await RisingEdge(dut.i_clk)
    dut.i_valid.value = 0
    for k in range(4):
        getattr(dut, f"i_data{k}_re").value = 0
        getattr(dut, f"i_data{k}_im").value = 0
    for _ in range(gap):
        await RisingEdge(dut.i_clk)


async def push_block(dut, samples, gap=0):
    for m in range(4):
        await push_group(
            dut, [samples[m], samples[m + 4], samples[m + 8], samples[m + 12]], gap
        )


async def run_blocks(dut, blocks, gap=0):
    rec = Recorder(dut).start()
    for samples in blocks:
        await push_block(dut, samples, gap)
    return await rec.stop()


def random_block(rng):
    return [
        complex(rng.randint(IN_MIN, IN_MAX), rng.randint(IN_MIN, IN_MAX))
        for _ in range(N)
    ]


def check(blocks, captured, inverse):
    expected = []
    for samples in blocks:
        expected.extend(process_block(samples, inverse))
    assert len(captured) == len(expected), (
        f"expected {len(expected)} output groups, got {len(captured)}"
    )
    for idx, (got, exp) in enumerate(zip(captured, expected)):
        assert got == exp, f"group {idx}: expected {exp}, got {got}"


@cocotb.test()
async def test_idle_produces_no_output(dut):
    await start(dut)
    for _ in range(100):
        await RisingEdge(dut.i_clk)
        assert dut.o_valid.value == 0, "o_valid asserted without any input"
    cocotb.log.info("No output while idle OK")


@cocotb.test()
async def test_pipeline_latency(dut):
    await start(dut)
    rng = random.Random(71)
    samples = random_block(rng)
    await push_group(dut, [samples[0], samples[4], samples[8], samples[12]])
    for step in range(LATENCY - 1):
        await RisingEdge(dut.i_clk)
        assert dut.o_valid.value == 0, (
            f"o_valid rose after {step + 1} clocks, expected {LATENCY}"
        )
    await RisingEdge(dut.i_clk)
    assert dut.o_valid.value == 1, f"o_valid must rise {LATENCY} clocks after i_valid"
    cocotb.log.info(f"Pipeline latency of {LATENCY} clocks confirmed OK")


@cocotb.test()
async def test_zero_input(dut):
    await start(dut)
    captured = await run_blocks(dut, [[complex(0, 0)] * N for _ in range(4)])
    assert len(captured) == 16, f"expected 16 groups, got {len(captured)}"
    for group in captured:
        assert group == [complex(0, 0)] * 4, (
            f"zero input must give zero output, got {group}"
        )
    cocotb.log.info("Zero input gives zero output OK")


@cocotb.test()
async def test_dc_input(dut):
    for inverse in (0, 1):
        await start(dut, inverse)
        amplitude = 64
        captured = await run_blocks(dut, [[complex(amplitude, 0)] * N])
        check([[complex(amplitude, 0)] * N], captured, inverse)
        assert captured[0][0].real > 0, "DC bin must carry the energy"
        for m in range(4):
            for k in range(1, 4):
                assert captured[m][k] == complex(0, 0), (
                    f"group {m} output {k} must be zero for a DC input, "
                    f"got {captured[m][k]}"
                )
        cocotb.log.info(f"inverse={inverse}: DC input concentrates in bin 0 OK")


@cocotb.test()
async def test_random_blocks_fft(dut):
    await start(dut, 0)
    rng = random.Random(72)
    blocks = [random_block(rng) for _ in range(100)]
    captured = await run_blocks(dut, blocks)
    check(blocks, captured, 0)
    cocotb.log.info(f"{len(blocks)} random FFT blocks match the bit-exact model OK")


@cocotb.test()
async def test_random_blocks_ifft(dut):
    await start(dut, 1)
    rng = random.Random(73)
    blocks = [random_block(rng) for _ in range(100)]
    captured = await run_blocks(dut, blocks, 0)
    check(blocks, captured, 1)
    cocotb.log.info(f"{len(blocks)} random IFFT blocks match the bit-exact model OK")


@cocotb.test()
async def test_varying_gaps(dut):
    rng = random.Random(74)
    for gap in [0, 1, 2, 3, 7, 15]:
        await start(dut, 0)
        blocks = [random_block(rng) for _ in range(6)]
        captured = await run_blocks(dut, blocks, gap=gap)
        check(blocks, captured, 0)
        cocotb.log.info(f"gap={gap} cycles between groups OK")


@cocotb.test()
async def test_twiddle_index_alignment(dut):
    await start(dut, 0)
    rng = random.Random(75)
    blocks = [random_block(rng) for _ in range(40)]
    captured = await run_blocks(dut, blocks, gap=15)
    check(blocks, captured, 0)
    cocotb.log.info(
        f"Twiddle index counter stays aligned over {len(blocks)} gapped blocks OK"
    )


@cocotb.test()
async def test_extreme_inputs(dut):
    await start(dut, 0)
    extremes = [IN_MIN, IN_MIN + 1, -1, 0, 1, IN_MAX - 1, IN_MAX]
    blocks = []
    for a in extremes:
        for b in extremes:
            blocks.append([complex(a, b) if i % 2 else complex(b, a) for i in range(N)])
    captured = await run_blocks(dut, blocks)
    check(blocks, captured, 0)
    saturated = sum(
        1
        for group in captured
        for value in group
        if int(value.real) in (-512, 511) or int(value.imag) in (-512, 511)
    )
    cocotb.log.info(
        f"{len(blocks)} extreme blocks, {saturated} saturated outputs OK"
    )


@cocotb.test()
async def test_all_ones_saturation(dut):
    await start(dut, 0)
    blocks = [[complex(IN_MIN, IN_MIN)] * N, [complex(IN_MAX, IN_MAX)] * N]
    captured = await run_blocks(dut, blocks)
    check(blocks, captured, 0)
    for group in captured:
        for value in group:
            assert -512 <= value.real <= 511 and -512 <= value.imag <= 511, (
                f"output {value} outside the {NB_TW}-bit range"
            )
    cocotb.log.info("Full-scale input stays inside the output range OK")


@cocotb.test()
async def test_enable_gating(dut):
    await start(dut, 0)
    rng = random.Random(76)
    blocks = [random_block(rng) for _ in range(4)]
    rec = Recorder(dut).start()
    for idx, samples in enumerate(blocks):
        if idx == 2:
            for _ in range(LATENCY + 2):
                await RisingEdge(dut.i_clk)
            dut.i_en.value = 0
            dut.i_valid.value = 1
            for k in range(4):
                getattr(dut, f"i_data{k}_re").value = 0x7F
                getattr(dut, f"i_data{k}_im").value = 0x7F
            for _ in range(12):
                await RisingEdge(dut.i_clk)
            dut.i_valid.value = 0
            for k in range(4):
                getattr(dut, f"i_data{k}_re").value = 0
                getattr(dut, f"i_data{k}_im").value = 0
            dut.i_en.value = 1
            await RisingEdge(dut.i_clk)
        await push_block(dut, samples)
    captured = await rec.stop()
    check(blocks, captured, 0)
    cocotb.log.info("Groups driven while i_en was low are ignored OK")


@cocotb.test()
async def test_mode_switch_between_blocks(dut):
    rng = random.Random(77)
    for inverse in [0, 1, 0, 1, 1, 0]:
        await start(dut, inverse)
        blocks = [random_block(rng) for _ in range(4)]
        captured = await run_blocks(dut, blocks)
        check(blocks, captured, inverse)
    cocotb.log.info("FFT and IFFT alternated between blocks OK")


@cocotb.test()
async def test_reset_midblock(dut):
    await start(dut, 0)
    rng = random.Random(78)
    partial = random_block(rng)
    await push_group(dut, [partial[0], partial[4], partial[8], partial[12]])
    await push_group(dut, [partial[1], partial[5], partial[9], partial[13]])
    await reset_dut(dut, 0)
    blocks = [random_block(rng) for _ in range(4)]
    captured = await run_blocks(dut, blocks)
    check(blocks, captured, 0)
    cocotb.log.info("Reset after a partial block realigns the twiddle counter OK")


@cocotb.test()
async def test_valid_pulse_count(dut):
    await start(dut, 0)
    rng = random.Random(79)
    n_blocks = 20
    blocks = [random_block(rng) for _ in range(n_blocks)]
    captured = await run_blocks(dut, blocks)
    assert len(captured) == 4 * n_blocks, (
        f"expected {4 * n_blocks} output pulses, got {len(captured)}"
    )
    cocotb.log.info(f"Exactly 4 output pulses per block over {n_blocks} blocks OK")


@cocotb.test()
async def test_against_reference_model(dut):
    rng = random.Random(80)
    for inverse in (0, 1):
        await start(dut, inverse)
        nbf = NBF_IFFT if inverse else NBF_FFT
        model = FFT4_Reference(
            NB_INPUT=NB_INPUT, NBF_INPUT=nbf, inverse=bool(inverse)
        )
        scale = 2 ** nbf
        tolerance = 2.0 / scale
        for _ in range(20):
            samples = random_block(rng)
            captured = await run_blocks(dut, [samples])
            flat = [value for group in captured for value in group]
            reference = model.process(
                [complex(v.real / scale, v.imag / scale) for v in samples]
            )
            for idx, (got, exp) in enumerate(zip(flat, reference)):
                assert abs(got.real / scale - exp.real) <= tolerance, (
                    f"index {idx}: real {got.real / scale} vs {exp.real}"
                )
                assert abs(got.imag / scale - exp.imag) <= tolerance, (
                    f"index {idx}: imag {got.imag / scale} vs {exp.imag}"
                )
        cocotb.log.info(f"inverse={inverse}: matches the fxpmath reference model OK")


@cocotb.test()
async def test_valid_is_held_while_disabled(dut):
    await start(dut, 0)
    rng = random.Random(81)
    samples = random_block(rng)
    for k in range(4):
        getattr(dut, f"i_data{k}_re").value = int(samples[k].real) & MASK
        getattr(dut, f"i_data{k}_im").value = int(samples[k].imag) & MASK
    dut.i_valid.value = 1
    for _ in range(200):
        await RisingEdge(dut.i_clk)
        if dut.o_valid.value == 1:
            break
    assert dut.o_valid.value == 1, "o_valid must rise for a continuous input stream"
    dut.i_en.value = 0
    dut.i_valid.value = 0
    await RisingEdge(dut.i_clk)
    frozen = [
        int(dut.o_data0_re.value),
        int(dut.o_data0_im.value),
        int(dut.o_data1_re.value),
        int(dut.o_data1_im.value),
    ]
    for _ in range(20):
        await RisingEdge(dut.i_clk)
        assert dut.o_valid.value == 1, (
            "o_valid is frozen rather than cleared by i_en, so downstream "
            "logic must be gated by the same enable"
        )
        assert [
            int(dut.o_data0_re.value),
            int(dut.o_data0_im.value),
            int(dut.o_data1_re.value),
            int(dut.o_data1_im.value),
        ] == frozen, "output data must stay frozen while i_en is low"
    dut.i_en.value = 1
    await RisingEdge(dut.i_clk)
    cocotb.log.info(
        "o_valid and the output data are frozen, not cleared, while i_en is low OK"
    )
