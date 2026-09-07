import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

NB = 8
MASK = (1 << NB) - 1
CLK_NS = 10
DESIGN_GAP = 7


async def reset_dut(dut):
    dut.i_rstn.value = 0
    dut.i_valid.value = 0
    dut.i_data_0r.value = 0
    dut.i_data_0i.value = 0
    dut.i_data_1r.value = 0
    dut.i_data_1i.value = 0
    for _ in range(4):
        await RisingEdge(dut.i_clk)
    dut.i_rstn.value = 1
    await RisingEdge(dut.i_clk)


async def start(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await reset_dut(dut)


def sample(dut):
    return (
        int(dut.o_data_0r.value) & MASK,
        int(dut.o_data_0i.value) & MASK,
        int(dut.o_data_1r.value) & MASK,
        int(dut.o_data_1i.value) & MASK,
    )


async def monitor(dut, results, n_expected, timeout=5000):
    cycles = 0
    while len(results) < n_expected and cycles < timeout:
        await RisingEdge(dut.i_clk)
        cycles += 1
        if dut.o_valid.value == 1:
            results.append(sample(dut))


async def push(dut, pair, gap=DESIGN_GAP):
    dut.i_valid.value = 1
    dut.i_data_0r.value = pair[0] & MASK
    dut.i_data_0i.value = pair[1] & MASK
    dut.i_data_1r.value = pair[2] & MASK
    dut.i_data_1i.value = pair[3] & MASK
    await RisingEdge(dut.i_clk)
    dut.i_valid.value = 0
    dut.i_data_0r.value = 0
    dut.i_data_0i.value = 0
    dut.i_data_1r.value = 0
    dut.i_data_1i.value = 0
    for _ in range(gap):
        await RisingEdge(dut.i_clk)


def expected_pair(first, second):
    return [
        (first[0], first[1], second[0], second[1]),
        (first[2], first[3], second[2], second[3]),
    ]


def make_pair(rng):
    return tuple(rng.randint(0, MASK) for _ in range(4))


async def run_blocks(dut, blocks, gap=DESIGN_GAP, timeout=20000):
    results = []
    mon = cocotb.start_soon(monitor(dut, results, 2 * len(blocks), timeout))
    for first, second in blocks:
        await push(dut, first, gap)
        await push(dut, second, gap)
    await mon
    return results


def expected_from_blocks(blocks):
    out = []
    for first, second in blocks:
        out.extend(expected_pair(first, second))
    return out


@cocotb.test()
async def test_single_block_commutation(dut):
    await start(dut)
    rng = random.Random(1)
    blocks = [(make_pair(rng), make_pair(rng))]
    results = await run_blocks(dut, blocks)
    expected = expected_from_blocks(blocks)
    assert results == expected, f"expected {expected}, got {results}"
    cocotb.log.info("Single block commutation OK")


@cocotb.test()
async def test_many_consecutive_blocks(dut):
    await start(dut)
    rng = random.Random(2)
    blocks = [(make_pair(rng), make_pair(rng)) for _ in range(32)]
    results = await run_blocks(dut, blocks, timeout=40000)
    expected = expected_from_blocks(blocks)
    assert len(results) == len(expected), (
        f"expected {len(expected)} outputs, got {len(results)}"
    )
    for idx, (got, exp) in enumerate(zip(results, expected)):
        assert got == exp, f"output {idx}: expected {exp}, got {got}"
    cocotb.log.info(f"{len(blocks)} consecutive blocks without reset OK")


@cocotb.test()
async def test_no_stall_after_first_block(dut):
    await start(dut)
    rng = random.Random(3)
    for block_idx in range(8):
        blocks = [(make_pair(rng), make_pair(rng))]
        results = await run_blocks(dut, blocks)
        expected = expected_from_blocks(blocks)
        assert len(results) == 2, (
            f"block {block_idx} produced {len(results)} outputs instead of 2"
        )
        assert results == expected, f"block {block_idx}: {expected} != {results}"
    cocotb.log.info("Every block after the first still produces exactly 2 outputs OK")


@cocotb.test()
async def test_varying_gaps(dut):
    rng = random.Random(4)
    for gap in [1, 2, 3, 5, 7, 11, 20]:
        await start(dut)
        blocks = [(make_pair(rng), make_pair(rng)) for _ in range(4)]
        results = await run_blocks(dut, blocks, gap=gap, timeout=20000)
        expected = expected_from_blocks(blocks)
        assert results == expected, (
            f"gap={gap}: expected {expected}, got {results}"
        )
        cocotb.log.info(f"gap={gap} cycles between valid pulses OK")


@cocotb.test()
async def test_valid_pulse_count(dut):
    await start(dut)
    rng = random.Random(5)
    n_blocks = 10
    results = []
    mon = cocotb.start_soon(monitor(dut, results, 2 * n_blocks + 4, 12000))
    for _ in range(n_blocks):
        await push(dut, make_pair(rng))
        await push(dut, make_pair(rng))
    for _ in range(200):
        await RisingEdge(dut.i_clk)
    assert len(results) == 2 * n_blocks, (
        f"expected exactly {2 * n_blocks} valid pulses, got {len(results)}"
    )
    mon.cancel()
    cocotb.log.info(f"Exactly {2 * n_blocks} output pulses for {n_blocks} blocks OK")


@cocotb.test()
async def test_idle_produces_no_output(dut):
    await start(dut)
    for _ in range(200):
        await RisingEdge(dut.i_clk)
        assert dut.o_valid.value == 0, "o_valid asserted without any input valid"
    cocotb.log.info("No output while idle OK")


@cocotb.test()
async def test_single_valid_waits_for_partner(dut):
    await start(dut)
    rng = random.Random(6)
    first = make_pair(rng)
    await push(dut, first)
    for _ in range(50):
        await RisingEdge(dut.i_clk)
        assert dut.o_valid.value == 0, "o_valid asserted after only one input pair"
    second = make_pair(rng)
    results = []
    mon = cocotb.start_soon(monitor(dut, results, 2))
    await push(dut, second)
    await mon
    assert results == expected_pair(first, second), (
        f"expected {expected_pair(first, second)}, got {results}"
    )
    cocotb.log.info("Half-filled switch waits for its partner OK")


@cocotb.test()
async def test_reset_midstream(dut):
    await start(dut)
    rng = random.Random(7)
    await push(dut, make_pair(rng))
    await reset_dut(dut)
    blocks = [(make_pair(rng), make_pair(rng)) for _ in range(3)]
    results = await run_blocks(dut, blocks)
    expected = expected_from_blocks(blocks)
    assert results == expected, (
        f"after mid-block reset expected {expected}, got {results}"
    )
    cocotb.log.info("Reset in the middle of a block realigns the switch OK")


@cocotb.test()
async def test_extreme_values(dut):
    await start(dut)
    extremes = [0, 1, MASK, MASK - 1, 1 << (NB - 1), (1 << (NB - 1)) - 1]
    blocks = []
    for a in extremes:
        for b in extremes:
            blocks.append(((a, b, a, b), (b, a, b, a)))
    results = await run_blocks(dut, blocks, timeout=40000)
    expected = expected_from_blocks(blocks)
    assert results == expected, "extreme value pattern mismatch"
    cocotb.log.info(f"{len(blocks)} extreme value blocks OK")


@cocotb.test()
async def test_output_holds_between_pulses(dut):
    await start(dut)
    rng = random.Random(8)
    first = make_pair(rng)
    second = make_pair(rng)
    results = []
    mon = cocotb.start_soon(monitor(dut, results, 2))
    await push(dut, first)
    await push(dut, second)
    await mon
    held = sample(dut)
    for _ in range(30):
        await RisingEdge(dut.i_clk)
        assert dut.o_valid.value == 0, "o_valid stayed high after the burst"
        assert sample(dut) == held, "output data changed while idle"
    cocotb.log.info("Output data is stable between bursts OK")


@cocotb.test()
async def test_minimum_valid_spacing(dut):
    await start(dut)
    rng = random.Random(11)
    blocks = [(make_pair(rng), make_pair(rng)) for _ in range(16)]
    results = await run_blocks(dut, blocks, gap=1, timeout=20000)
    expected = expected_from_blocks(blocks)
    assert results == expected, (
        f"one idle cycle between valid pulses must be supported: "
        f"expected {expected}, got {results}"
    )
    cocotb.log.info("Tightest supported input rate (one valid every 2 cycles) OK")


@cocotb.test()
async def test_back_to_back_valid_is_out_of_spec(dut):
    await start(dut)
    rng = random.Random(12)
    blocks = [(make_pair(rng), make_pair(rng)) for _ in range(4)]
    results = await run_blocks(dut, blocks, gap=0, timeout=20000)
    assert len(results) == len(expected_from_blocks(blocks)), (
        "the switch must keep pulsing o_valid even when driven faster than spec"
    )
    cocotb.log.info(
        "Continuous i_valid overruns the 4-word storage as expected; "
        "the pipeline requires at least one idle cycle between valid pulses"
    )
