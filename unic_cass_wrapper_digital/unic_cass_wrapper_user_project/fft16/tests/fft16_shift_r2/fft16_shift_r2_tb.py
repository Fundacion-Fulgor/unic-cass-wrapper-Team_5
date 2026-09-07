import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

CLK_NS = 10
NB_DATA = 8
MASK = (1 << NB_DATA) - 1
N_TAP = 3
GROUP = 4
FIRST_OUT = 2
TAPS = [3, 1]

DATA_MIN = -(1 << (NB_DATA - 1))
DATA_MAX = (1 << (NB_DATA - 1)) - 1


def to_signed(value):
    value = int(value) & MASK
    return value - (1 << NB_DATA) if value >= (1 << (NB_DATA - 1)) else value


async def reset_dut(dut):
    dut.i_rstn.value = 0
    dut.i_en.value = 0
    dut.i_valid.value = 0
    dut.i_data_re.value = 0
    dut.i_data_im.value = 0
    for _ in range(4):
        await RisingEdge(dut.i_clk)
    dut.i_rstn.value = 1
    dut.i_en.value = 1
    await RisingEdge(dut.i_clk)


async def start(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await reset_dut(dut)


def read_taps(dut):
    return [
        (to_signed(dut.o_data0_re.value), to_signed(dut.o_data0_im.value)),
        (to_signed(dut.o_data1_re.value), to_signed(dut.o_data1_im.value)),
    ]


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
                self.captured.append(read_taps(self.dut))

    async def stop(self, drain=4):
        for _ in range(drain):
            await RisingEdge(self.dut.i_clk)
        self.running = False
        await RisingEdge(self.dut.i_clk)
        return self.captured


async def push(dut, sample, gap=0):
    dut.i_valid.value = 1
    dut.i_data_re.value = sample[0] & MASK
    dut.i_data_im.value = sample[1] & MASK
    await RisingEdge(dut.i_clk)
    dut.i_valid.value = 0
    dut.i_data_re.value = 0
    dut.i_data_im.value = 0
    for _ in range(gap):
        await RisingEdge(dut.i_clk)


def expected_groups(samples):
    groups = []
    for n in range(1, len(samples) + 1):
        if (n - 1) % GROUP >= FIRST_OUT:
            groups.append([samples[n - tap] for tap in TAPS])
    return groups


def make_samples(rng, count):
    return [
        (rng.randint(DATA_MIN, DATA_MAX), rng.randint(DATA_MIN, DATA_MAX))
        for _ in range(count)
    ]


async def run_stream(dut, samples, gap=0):
    rec = Recorder(dut).start()
    for sample in samples:
        await push(dut, sample, gap)
    return await rec.stop()


@cocotb.test()
async def test_reset_clears_valid(dut):
    await start(dut)
    for _ in range(50):
        await RisingEdge(dut.i_clk)
        assert dut.o_valid.value == 0, "o_valid asserted without any input"
    cocotb.log.info("Reset leaves o_valid low OK")


@cocotb.test()
async def test_no_output_before_pipeline_fills(dut):
    await start(dut)
    rec = Recorder(dut).start()
    rng = random.Random(51)
    for sample in make_samples(rng, FIRST_OUT):
        await push(dut, sample)
    captured = await rec.stop()
    assert captured == [], (
        f"no output expected before {FIRST_OUT + 1} valid samples, "
        f"got {len(captured)}"
    )
    cocotb.log.info(f"No output during the first {FIRST_OUT} samples OK")


@cocotb.test()
async def test_single_block_tap_alignment(dut):
    await start(dut)
    rng = random.Random(52)
    samples = make_samples(rng, GROUP)
    captured = await run_stream(dut, samples)
    expected = expected_groups(samples)
    assert len(captured) == 2, f"expected 2 pairs, got {len(captured)}"
    assert captured == expected, f"expected {expected}, got {captured}"
    cocotb.log.info("Radix-2 tap alignment for one block OK")


@cocotb.test()
async def test_decimation_groups_are_correct(dut):
    await start(dut)
    samples = [(i, -i) for i in range(GROUP * 2)]
    captured = await run_stream(dut, samples)
    for block in range(2):
        base = block * GROUP
        for m in range(2):
            got = [value for value, _ in captured[block * 2 + m]]
            assert got == [base + m, base + m + 2], (
                f"pair {m} of block {block} must be x[{base + m}], "
                f"x[{base + m + 2}], got {got}"
            )
    cocotb.log.info("Pairs follow the radix-2 decimation pattern OK")


@cocotb.test()
async def test_many_consecutive_blocks(dut):
    await start(dut)
    rng = random.Random(53)
    n_blocks = 24
    samples = make_samples(rng, GROUP * n_blocks)
    captured = await run_stream(dut, samples)
    expected = expected_groups(samples)
    assert len(captured) == 2 * n_blocks, (
        f"expected {2 * n_blocks} pairs over {n_blocks} blocks, got {len(captured)}"
    )
    assert captured == expected, "tap alignment lost across consecutive blocks"
    cocotb.log.info(f"{n_blocks} consecutive blocks stay aligned OK")


@cocotb.test()
async def test_varying_gaps(dut):
    rng = random.Random(54)
    for gap in [0, 1, 3, 7, 15]:
        await start(dut)
        samples = make_samples(rng, GROUP * 3)
        captured = await run_stream(dut, samples, gap=gap)
        assert captured == expected_groups(samples), (
            f"gap={gap}: tap alignment mismatch"
        )
        cocotb.log.info(f"gap={gap} cycles between samples OK")


@cocotb.test()
async def test_clk_en_gating(dut):
    await start(dut)
    rng = random.Random(55)
    samples = make_samples(rng, GROUP * 2)
    rec = Recorder(dut).start()
    for idx, sample in enumerate(samples):
        if idx == 5:
            dut.i_en.value = 0
            dut.i_valid.value = 1
            dut.i_data_re.value = 0x7F
            dut.i_data_im.value = 0x7F
            for _ in range(10):
                await RisingEdge(dut.i_clk)
            dut.i_valid.value = 0
            dut.i_en.value = 1
            await RisingEdge(dut.i_clk)
        await push(dut, sample)
    captured = await rec.stop()
    assert captured == expected_groups(samples), (
        "samples driven while i_en was low must be ignored"
    )
    cocotb.log.info("i_en gating drops samples without losing alignment OK")


@cocotb.test()
async def test_reset_realigns(dut):
    await start(dut)
    rng = random.Random(56)
    for sample in make_samples(rng, 3):
        await push(dut, sample)
    await reset_dut(dut)
    samples = make_samples(rng, GROUP * 2)
    captured = await run_stream(dut, samples)
    assert captured == expected_groups(samples), (
        "reset must restart the valid counter alignment"
    )
    cocotb.log.info("Reset mid-block realigns the decimation phase OK")


@cocotb.test()
async def test_valid_pulse_count(dut):
    await start(dut)
    rng = random.Random(57)
    n_blocks = 20
    samples = make_samples(rng, GROUP * n_blocks)
    captured = await run_stream(dut, samples)
    assert len(captured) == 2 * n_blocks, (
        f"expected exactly {2 * n_blocks} o_valid pulses, got {len(captured)}"
    )
    cocotb.log.info("Exactly 2 output pulses per 4 input samples OK")


@cocotb.test()
async def test_extreme_values(dut):
    await start(dut)
    extremes = [DATA_MIN, DATA_MIN + 1, -1, 0, 1, DATA_MAX - 1, DATA_MAX]
    samples = [
        (extremes[i % len(extremes)], extremes[(i * 3) % len(extremes)])
        for i in range(GROUP * 3)
    ]
    captured = await run_stream(dut, samples)
    assert captured == expected_groups(samples), "extreme value pattern mismatch"
    cocotb.log.info("Extreme signed values pass through unchanged OK")


@cocotb.test()
async def test_re_im_independent(dut):
    await start(dut)
    rng = random.Random(58)
    samples = make_samples(rng, GROUP * 2)
    captured = await run_stream(dut, samples)
    for group, expected in zip(captured, expected_groups(samples)):
        for (got_re, got_im), (exp_re, exp_im) in zip(group, expected):
            assert got_re == exp_re, "real tap corrupted"
            assert got_im == exp_im, "imaginary tap corrupted"
    cocotb.log.info("Real and imaginary delay lines are independent OK")


@cocotb.test()
async def test_long_random_stream(dut):
    await start(dut)
    rng = random.Random(59)
    samples = make_samples(rng, GROUP * 64)
    captured = await run_stream(dut, samples)
    expected = expected_groups(samples)
    assert len(captured) == len(expected)
    for idx, (got, exp) in enumerate(zip(captured, expected)):
        assert got == exp, f"group {idx}: expected {exp}, got {got}"
    cocotb.log.info(f"{len(samples)} sample stream, {len(captured)} groups OK")
