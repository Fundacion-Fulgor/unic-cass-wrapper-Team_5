import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
import random


def to_signed(val, bits):
    if val >= (1 << (bits - 1)):
        val -= (1 << bits)
    return val


async def reset_dut(dut):
    dut.i_rstn.value    = 0
    dut.i_en.value   = 0
    dut.i_valid.value    = 0
    dut.i_tx_ready.value = 0
    for k in range(8):
        getattr(dut, f"i_data{k}_re").value = 0
        getattr(dut, f"i_data{k}_im").value = 0
    await RisingEdge(dut.i_clk)
    await RisingEdge(dut.i_clk)
    dut.i_rstn.value  = 1
    dut.i_en.value = 1
    await RisingEdge(dut.i_clk)


async def feed_batch(dut, batch):
    for k in range(8):
        getattr(dut, f"i_data{k}_re").value = batch[k][0] & 0xFF
        getattr(dut, f"i_data{k}_im").value = batch[k][1] & 0xFF
    dut.i_valid.value = 1
    await RisingEdge(dut.i_clk)
    dut.i_valid.value = 0


async def collect_outputs(dut, n_samples, busy_cycles, timeout=2000):
    """
    Collect n_samples using the buffer handshake protocol:
      1. i_tx_ready=1 → buffer presents sample with o_valid=1 (S_WAIT_RDY → S_WAIT_BSY)
      2. Capture o_data_re/im on the cycle o_valid=1
      3. i_tx_ready=0 for busy_cycles → buffer advances read_ptr (S_WAIT_BSY → S_WAIT_RDY)
    """
    NB_DATA = 8
    results = []
    cycles  = 0

    while len(results) < n_samples and cycles < timeout:

        dut.i_tx_ready.value = 1
        while cycles < timeout:
            await RisingEdge(dut.i_clk)
            cycles += 1
            if dut.o_valid.value == 1:
                re = to_signed(int(dut.o_data_re.value), NB_DATA)
                im = to_signed(int(dut.o_data_im.value), NB_DATA)
                results.append((re, im))
                break

        dut.i_tx_ready.value = 0
        for _ in range(busy_cycles):
            await RisingEdge(dut.i_clk)
            cycles += 1

    dut.i_tx_ready.value = 0
    return results


@cocotb.test()
async def test_basic_ordering(dut):
    """
    Feed 2 batches of 8, collect 16 outputs.
    Verify flat ordering: batch0[0..7] followed by batch1[0..7].
    busy_cycles=2 minimum to ensure S_WAIT_BSY sees !i_tx_ready.
    """
    clock = Clock(dut.i_clk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    batch0   = [(i,     -i    ) for i in range(8)]
    batch1   = [(i + 8, -(i+8)) for i in range(8)]
    expected = batch0 + batch1

    cocotb.log.info("--- test_basic_ordering ---")

    await feed_batch(dut, batch0)
    await feed_batch(dut, batch1)

    results = await collect_outputs(dut, 16, busy_cycles=2)

    assert len(results) == 16, f"Expected 16 samples, got {len(results)}"
    for idx, (got, exp) in enumerate(zip(results, expected)):
        assert got == exp, f"Mismatch at index {idx}: got {got}, expected {exp}"
        cocotb.log.info(f"[{idx:2d}] re={got[0]:+4d} im={got[1]:+4d}  OK")

    cocotb.log.info("test_basic_ordering PASSED.")


@cocotb.test()
async def test_backpressure(dut):
    """
    Receiver stays busy for 5 cycles after each item.
    Verifies FSM waits in S_WAIT_BSY without dropping data.
    """
    clock = Clock(dut.i_clk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    batch0   = [(i * 3,      i * 2     ) for i in range(8)]
    batch1   = [(i * 3 + 24, i * 2 + 16) for i in range(8)]
    expected = batch0 + batch1

    cocotb.log.info("--- test_backpressure ---")

    await feed_batch(dut, batch0)
    await feed_batch(dut, batch1)

    results = await collect_outputs(dut, 16, busy_cycles=5)

    assert len(results) == 16, f"Expected 16 samples, got {len(results)}"
    for idx, (got, exp) in enumerate(zip(results, expected)):
        assert got == exp, f"Mismatch at index {idx}: got {got}, expected {exp}"
        cocotb.log.info(f"[{idx:2d}] re={got[0]:+4d} im={got[1]:+4d}  OK")

    cocotb.log.info("test_backpressure PASSED.")


@cocotb.test()
async def test_delayed_ready(dut):
    """
    Feed both batches, wait 20 cycles before starting collection.
    Verifies S_WAIT_RDY holds correctly with no data loss.
    """
    clock = Clock(dut.i_clk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    batch0   = [( 10 + i,  -(10 + i)) for i in range(8)]
    batch1   = [(-10 - i,   (10 + i)) for i in range(8)]
    expected = batch0 + batch1

    cocotb.log.info("--- test_delayed_ready ---")

    await feed_batch(dut, batch0)
    await feed_batch(dut, batch1)

    dut.i_tx_ready.value = 0
    for _ in range(20):
        await RisingEdge(dut.i_clk)

    results = await collect_outputs(dut, 16, busy_cycles=2)

    assert len(results) == 16, f"Expected 16 samples, got {len(results)}"
    for idx, (got, exp) in enumerate(zip(results, expected)):
        assert got == exp, f"Mismatch at index {idx}: got {got}, expected {exp}"
        cocotb.log.info(f"[{idx:2d}] re={got[0]:+4d} im={got[1]:+4d}  OK")

    cocotb.log.info("test_delayed_ready PASSED.")


@cocotb.test()
async def test_random(dut):
    """
    Random signed 8-bit values, random busy duration (2..8 cycles).
    Verifies ordering is preserved end-to-end.
    """
    clock = Clock(dut.i_clk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    NB_DATA = 8
    MIN_VAL = -(1 << (NB_DATA - 1))
    MAX_VAL =  (1 << (NB_DATA - 1)) - 1

    random.seed(42)

    batch0   = [(random.randint(MIN_VAL, MAX_VAL),
                 random.randint(MIN_VAL, MAX_VAL)) for _ in range(8)]
    batch1   = [(random.randint(MIN_VAL, MAX_VAL),
                 random.randint(MIN_VAL, MAX_VAL)) for _ in range(8)]
    expected = batch0 + batch1

    cocotb.log.info("--- test_random ---")

    await feed_batch(dut, batch0)
    await feed_batch(dut, batch1)

    busy    = random.randint(2, 8)
    results = await collect_outputs(dut, 16, busy_cycles=busy)

    assert len(results) == 16, f"Expected 16 samples, got {len(results)}"
    for idx, (got, exp) in enumerate(zip(results, expected)):
        assert got == exp, f"Mismatch at index {idx}: got {got}, expected {exp}"
        cocotb.log.info(f"[{idx:2d}] re={got[0]:+4d} im={got[1]:+4d}  OK")

    cocotb.log.info("test_random PASSED.")

NB_DATA = 8
MIN_VAL = -(1 << (NB_DATA - 1))
MAX_VAL = (1 << (NB_DATA - 1)) - 1
EXTREMES = [MIN_VAL, MIN_VAL + 1, -1, 0, 1, MAX_VAL - 1, MAX_VAL]


async def feed_and_collect(dut, batch0, batch1, busy_cycles=2):
    await feed_batch(dut, batch0)
    await feed_batch(dut, batch1)
    return await collect_outputs(dut, 16, busy_cycles=busy_cycles)


def assert_sequence(results, expected, context=""):
    assert len(results) == len(expected), (
        f"{context}expected {len(expected)} samples, got {len(results)}"
    )
    for idx, (got, exp) in enumerate(zip(results, expected)):
        assert got == exp, f"{context}index {idx}: expected {exp}, got {got}"


@cocotb.test()
async def test_extreme_values(dut):
    cocotb.start_soon(Clock(dut.i_clk, 10, unit="ns").start())
    await reset_dut(dut)

    batch0 = [(EXTREMES[i % 7], EXTREMES[(i * 3) % 7]) for i in range(8)]
    batch1 = [(EXTREMES[(i * 5) % 7], EXTREMES[(i * 2) % 7]) for i in range(8)]

    results = await feed_and_collect(dut, batch0, batch1)
    assert_sequence(results, batch0 + batch1)
    cocotb.log.info("Extreme signed values pass through unchanged OK")


@cocotb.test()
async def test_no_output_after_single_batch(dut):
    cocotb.start_soon(Clock(dut.i_clk, 10, unit="ns").start())
    await reset_dut(dut)

    await feed_batch(dut, [(i, -i) for i in range(8)])
    dut.i_tx_ready.value = 1
    for _ in range(100):
        await RisingEdge(dut.i_clk)
        assert dut.o_valid.value == 0, (
            "the buffer must wait for the second batch before streaming out"
        )
    dut.i_tx_ready.value = 0
    cocotb.log.info("A single batch does not start the readout OK")


@cocotb.test()
async def test_many_consecutive_frames(dut):
    cocotb.start_soon(Clock(dut.i_clk, 10, unit="ns").start())
    await reset_dut(dut)

    random.seed(101)
    for frame in range(12):
        batch0 = [
            (random.randint(MIN_VAL, MAX_VAL), random.randint(MIN_VAL, MAX_VAL))
            for _ in range(8)
        ]
        batch1 = [
            (random.randint(MIN_VAL, MAX_VAL), random.randint(MIN_VAL, MAX_VAL))
            for _ in range(8)
        ]
        results = await feed_and_collect(dut, batch0, batch1)
        assert_sequence(results, batch0 + batch1, f"frame {frame}: ")
    cocotb.log.info("12 consecutive 16-sample frames without reset OK")


@cocotb.test()
async def test_busy_cycle_sweep(dut):
    cocotb.start_soon(Clock(dut.i_clk, 10, unit="ns").start())
    random.seed(102)
    for busy in range(1, 9):
        await reset_dut(dut)
        batch0 = [(i + busy, -(i + busy)) for i in range(8)]
        batch1 = [(i + 8 + busy, -(i + 8 + busy)) for i in range(8)]
        results = await feed_and_collect(dut, batch0, batch1, busy_cycles=busy)
        assert_sequence(results, batch0 + batch1, f"busy={busy}: ")
        cocotb.log.info(f"  busy_cycles={busy} OK")
    cocotb.log.info("Backpressure duration sweep OK")


@cocotb.test()
async def test_valid_ignored_during_readout(dut):
    cocotb.start_soon(Clock(dut.i_clk, 10, unit="ns").start())
    await reset_dut(dut)

    batch0 = [(i, -i) for i in range(8)]
    batch1 = [(i + 8, -(i + 8)) for i in range(8)]
    await feed_batch(dut, batch0)
    await feed_batch(dut, batch1)

    results = []
    cycles = 0
    intruder = [(99, 99)] * 8
    while len(results) < 16 and cycles < 2000:
        dut.i_tx_ready.value = 1
        while cycles < 2000:
            await RisingEdge(dut.i_clk)
            cycles += 1
            if dut.o_valid.value == 1:
                results.append(
                    (
                        to_signed(int(dut.o_data_re.value), 8),
                        to_signed(int(dut.o_data_im.value), 8),
                    )
                )
                break
        dut.i_tx_ready.value = 0
        if len(results) == 4:
            await feed_batch(dut, intruder)
            cycles += 1
        for _ in range(2):
            await RisingEdge(dut.i_clk)
            cycles += 1
    dut.i_tx_ready.value = 0

    assert_sequence(results, batch0 + batch1)
    cocotb.log.info("i_valid asserted during readout does not corrupt the frame OK")


@cocotb.test()
async def test_reset_midstream(dut):
    cocotb.start_soon(Clock(dut.i_clk, 10, unit="ns").start())
    await reset_dut(dut)

    await feed_batch(dut, [(50, 50)] * 8)
    await reset_dut(dut)

    batch0 = [(i * 2, -i * 2) for i in range(8)]
    batch1 = [(i * 2 + 16, -(i * 2 + 16)) for i in range(8)]
    results = await feed_and_collect(dut, batch0, batch1)
    assert_sequence(results, batch0 + batch1)
    cocotb.log.info("Reset after a half-filled frame realigns the buffer OK")


@cocotb.test()
async def test_reset_during_readout(dut):
    cocotb.start_soon(Clock(dut.i_clk, 10, unit="ns").start())
    await reset_dut(dut)

    await feed_batch(dut, [(1, 1)] * 8)
    await feed_batch(dut, [(2, 2)] * 8)
    await collect_outputs(dut, 4, busy_cycles=2)
    await reset_dut(dut)

    batch0 = [(i + 30, -(i + 30)) for i in range(8)]
    batch1 = [(i + 40, -(i + 40)) for i in range(8)]
    results = await feed_and_collect(dut, batch0, batch1)
    assert_sequence(results, batch0 + batch1)
    cocotb.log.info("Reset in the middle of a readout recovers cleanly OK")


@cocotb.test()
async def test_clk_en_gating(dut):
    cocotb.start_soon(Clock(dut.i_clk, 10, unit="ns").start())
    await reset_dut(dut)

    dut.i_en.value = 0
    await feed_batch(dut, [(77, 77)] * 8)
    for _ in range(20):
        await RisingEdge(dut.i_clk)
    dut.i_en.value = 1
    await RisingEdge(dut.i_clk)

    batch0 = [(i + 5, -(i + 5)) for i in range(8)]
    batch1 = [(i + 15, -(i + 15)) for i in range(8)]
    results = await feed_and_collect(dut, batch0, batch1)
    assert_sequence(results, batch0 + batch1)
    cocotb.log.info("Batches fed while i_en was low are ignored OK")


@cocotb.test()
async def test_output_valid_is_single_cycle(dut):
    cocotb.start_soon(Clock(dut.i_clk, 10, unit="ns").start())
    await reset_dut(dut)

    await feed_batch(dut, [(i, i) for i in range(8)])
    await feed_batch(dut, [(i + 8, i + 8) for i in range(8)])

    pulses = 0
    consecutive = 0
    dut.i_tx_ready.value = 1
    for _ in range(60):
        await RisingEdge(dut.i_clk)
        if dut.o_valid.value == 1:
            pulses += 1
            consecutive += 1
            assert consecutive <= 1, "o_valid stayed high for more than one cycle"
        else:
            consecutive = 0
    dut.i_tx_ready.value = 0
    assert pulses >= 1, "no output pulse observed"
    cocotb.log.info(f"o_valid pulses for a single cycle ({pulses} pulses seen) OK")


@cocotb.test()
async def test_ready_never_asserted(dut):
    cocotb.start_soon(Clock(dut.i_clk, 10, unit="ns").start())
    await reset_dut(dut)

    await feed_batch(dut, [(3, 4)] * 8)
    await feed_batch(dut, [(5, 6)] * 8)

    dut.i_tx_ready.value = 0
    for _ in range(200):
        await RisingEdge(dut.i_clk)
        assert dut.o_valid.value == 0, "o_valid must wait for i_tx_ready"

    results = await collect_outputs(dut, 16, busy_cycles=2)
    assert_sequence(results, [(3, 4)] * 8 + [(5, 6)] * 8)
    cocotb.log.info("The frame is held indefinitely until i_tx_ready arrives OK")


@cocotb.test()
async def test_alternating_extremes_long_run(dut):
    cocotb.start_soon(Clock(dut.i_clk, 10, unit="ns").start())
    await reset_dut(dut)

    random.seed(103)
    for frame in range(8):
        batch0 = [(MIN_VAL if (i + frame) % 2 else MAX_VAL, MAX_VAL) for i in range(8)]
        batch1 = [(MAX_VAL if (i + frame) % 2 else MIN_VAL, MIN_VAL) for i in range(8)]
        busy = random.randint(1, 6)
        results = await feed_and_collect(dut, batch0, batch1, busy_cycles=busy)
        assert_sequence(results, batch0 + batch1, f"frame {frame}: ")
    cocotb.log.info("8 frames of alternating full-scale values OK")
