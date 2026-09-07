import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
import random

CLK_NS        = 20
NB_DATA       = 8
N_DATA        = 16
TIMEOUT_CYCLES = 5000


def to_signed(val, bits):
    if val >= (1 << (bits - 1)):
        val -= (1 << bits)
    return val


async def reset_dut(dut):
    dut.i_rstn.value  = 0
    dut.i_en.value = 0
    dut.i_valid.value  = 0
    for k in range(8):
        getattr(dut, f"i_data{k}_re").value = 0
        getattr(dut, f"i_data{k}_im").value = 0
    for _ in range(4):
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


async def capture_serial_output(dut, n_samples):
    """
    Captures n_samples from the serial output by reconstructing
    the bit stream. First sample is preceded by a start bit,
    the rest are sent directly.
    Returns list of (re, im) signed tuples.
    """
    results = []

    for idx in range(n_samples):
        if idx == 0:
            cycles = 0
            while cycles < TIMEOUT_CYCLES:
                await RisingEdge(dut.i_clk)
                cycles += 1
                if dut.o_data.value == 1:
                    break
            else:
                assert False, "Timeout: start bit never detected"
        else:
            await RisingEdge(dut.i_clk)
            await RisingEdge(dut.i_clk)  # extra cycle for o_data to register first bit

        received = 0
        for _ in range(2 * NB_DATA):
            await RisingEdge(dut.i_clk)
            received = (received << 1) | int(dut.o_data.value)

        re = to_signed((received >> NB_DATA) & 0xFF, NB_DATA)
        im = to_signed( received             & 0xFF, NB_DATA)
        results.append((re, im))

    return results


@cocotb.test()
async def test_basic_integration(dut):
    """
    Feed 2 batches of 8, verify all 16 samples come out in order
    through the serial output.
    """
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await reset_dut(dut)
    cocotb.log.info("--- test_basic_integration ---")

    batch0   = [(i,     -i    ) for i in range(8)]
    batch1   = [(i + 8, -(i+8)) for i in range(8)]
    expected = batch0 + batch1

    await feed_batch(dut, batch0)
    await feed_batch(dut, batch1)

    results = await capture_serial_output(dut, N_DATA)

    assert len(results) == N_DATA, f"Expected {N_DATA} samples, got {len(results)}"
    for idx, (got, exp) in enumerate(zip(results, expected)):
        assert got == exp, f"[{idx}] got {got}, expected {exp}"
        cocotb.log.info(f"  [{idx:2d}] re={got[0]:+4d} im={got[1]:+4d}  OK")

    cocotb.log.info("test_basic_integration PASSED.")


@cocotb.test()
async def test_start_bit_framing(dut):
    """
    Verifies that the start bit appears exactly once at the beginning
    of each batch of N_DATA samples, and not between samples.
    """
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await reset_dut(dut)
    cocotb.log.info("--- test_start_bit_framing ---")

    batch0 = [(i * 2, i * 2 + 1) for i in range(8)]
    batch1 = [(i * 3, i * 3 + 1) for i in range(8)]

    await feed_batch(dut, batch0)
    await feed_batch(dut, batch1)

    # Wait for start bit of first batch
    cycles = 0
    while cycles < TIMEOUT_CYCLES:
        await RisingEdge(dut.i_clk)
        cycles += 1
        if dut.o_data.value == 1:
            break
    else:
        assert False, "Timeout: first start bit never detected"

    cocotb.log.info("  First batch start bit detected  OK")

    # Drain first batch (consume bits without checking for start)
    for _ in range(N_DATA * 2 * NB_DATA):
        await RisingEdge(dut.i_clk)

    cocotb.log.info("  First batch drained  OK")
    cocotb.log.info("test_start_bit_framing PASSED.")


@cocotb.test()
async def test_random_data(dut):
    """
    Random signed 8-bit values across 2 batches.
    Verifies end-to-end ordering is preserved.
    """
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await reset_dut(dut)
    cocotb.log.info("--- test_random_data ---")

    random.seed(99)
    MIN_VAL = -(1 << (NB_DATA - 1))
    MAX_VAL =  (1 << (NB_DATA - 1)) - 1

    batch0   = [(random.randint(MIN_VAL, MAX_VAL),
                 random.randint(MIN_VAL, MAX_VAL)) for _ in range(8)]
    batch1   = [(random.randint(MIN_VAL, MAX_VAL),
                 random.randint(MIN_VAL, MAX_VAL)) for _ in range(8)]
    expected = batch0 + batch1

    await feed_batch(dut, batch0)
    await feed_batch(dut, batch1)

    results = await capture_serial_output(dut, N_DATA)

    assert len(results) == N_DATA, f"Expected {N_DATA} samples, got {len(results)}"
    for idx, (got, exp) in enumerate(zip(results, expected)):
        assert got == exp, f"[{idx}] got {got}, expected {exp}"
        cocotb.log.info(f"  [{idx:2d}] re={got[0]:+4d} im={got[1]:+4d}  OK")

    cocotb.log.info("test_random_data PASSED.")


@cocotb.test()
async def test_consecutive_frame_batches(dut):
    """
    Sends two full frames back to back and verifies each comes
    out correctly with its start bit.
    """
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await reset_dut(dut)
    cocotb.log.info("--- test_consecutive_frame_batches ---")

    random.seed(7)
    MIN_VAL = -(1 << (NB_DATA - 1))
    MAX_VAL =  (1 << (NB_DATA - 1)) - 1

    for frame in range(2):
        batch0   = [(random.randint(MIN_VAL, MAX_VAL),
                     random.randint(MIN_VAL, MAX_VAL)) for _ in range(8)]
        batch1   = [(random.randint(MIN_VAL, MAX_VAL),
                     random.randint(MIN_VAL, MAX_VAL)) for _ in range(8)]
        expected = batch0 + batch1

        await feed_batch(dut, batch0)
        await feed_batch(dut, batch1)

        results = await capture_serial_output(dut, N_DATA)

        assert len(results) == N_DATA, \
            f"Frame {frame}: expected {N_DATA} samples, got {len(results)}"
        for idx, (got, exp) in enumerate(zip(results, expected)):
            assert got == exp, f"Frame {frame}[{idx}]: got {got}, expected {exp}"
            cocotb.log.info(f"  Frame {frame}[{idx:2d}] re={got[0]:+4d} im={got[1]:+4d}  OK")

        cocotb.log.info(f"  Frame {frame} PASSED.")

    cocotb.log.info("test_consecutive_frame_batches PASSED.")

MIN_VAL = -(1 << (NB_DATA - 1))
MAX_VAL = (1 << (NB_DATA - 1)) - 1
EXTREMES = [MIN_VAL, MIN_VAL + 1, -1, 0, 1, MAX_VAL - 1, MAX_VAL]


async def feed_frame(dut, batch0, batch1):
    await feed_batch(dut, batch0)
    await feed_batch(dut, batch1)


def assert_frame(results, expected, context=""):
    assert len(results) == len(expected), (
        f"{context}expected {len(expected)} samples, got {len(results)}"
    )
    for idx, (got, exp) in enumerate(zip(results, expected)):
        assert got == exp, f"{context}index {idx}: expected {exp}, got {got}"


def random_batch(rng):
    return [
        (rng.randint(MIN_VAL, MAX_VAL), rng.randint(MIN_VAL, MAX_VAL))
        for _ in range(8)
    ]


@cocotb.test()
async def test_extreme_values_end_to_end(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await reset_dut(dut)

    batch0 = [(EXTREMES[i % 7], EXTREMES[(i * 3) % 7]) for i in range(8)]
    batch1 = [(EXTREMES[(i * 5) % 7], EXTREMES[(i * 2) % 7]) for i in range(8)]

    await feed_frame(dut, batch0, batch1)
    results = await capture_serial_output(dut, N_DATA)
    assert_frame(results, batch0 + batch1)
    cocotb.log.info("Full-scale values survive the buffer and serialiser OK")


@cocotb.test()
async def test_all_zero_frame(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await reset_dut(dut)

    await feed_frame(dut, [(0, 0)] * 8, [(0, 0)] * 8)
    results = await capture_serial_output(dut, N_DATA)
    assert_frame(results, [(0, 0)] * 16)
    cocotb.log.info("An all-zero frame still frames correctly OK")


@cocotb.test()
async def test_all_ones_frame(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await reset_dut(dut)

    await feed_frame(dut, [(-1, -1)] * 8, [(-1, -1)] * 8)
    results = await capture_serial_output(dut, N_DATA)
    assert_frame(results, [(-1, -1)] * 16)
    cocotb.log.info("An all-ones frame does not confuse the start-bit framing OK")


@cocotb.test()
async def test_many_consecutive_frames(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await reset_dut(dut)

    rng = random.Random(131)
    for frame in range(8):
        batch0 = random_batch(rng)
        batch1 = random_batch(rng)
        await feed_frame(dut, batch0, batch1)
        results = await capture_serial_output(dut, N_DATA)
        assert_frame(results, batch0 + batch1, f"frame {frame}: ")
    cocotb.log.info("8 consecutive frames through buffer and serialiser OK")


@cocotb.test()
async def test_delayed_second_batch(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await reset_dut(dut)

    rng = random.Random(132)
    batch0 = random_batch(rng)
    batch1 = random_batch(rng)

    await feed_batch(dut, batch0)
    for _ in range(120):
        await RisingEdge(dut.i_clk)
        assert dut.o_data.value == 0, (
            "nothing may be transmitted before the frame is complete"
        )
    await feed_batch(dut, batch1)
    results = await capture_serial_output(dut, N_DATA)
    assert_frame(results, batch0 + batch1)
    cocotb.log.info("A long gap between the two half-batches is tolerated OK")


@cocotb.test()
async def test_reset_between_frames(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await reset_dut(dut)

    rng = random.Random(133)
    await feed_batch(dut, random_batch(rng))
    await reset_dut(dut)

    batch0 = random_batch(rng)
    batch1 = random_batch(rng)
    await feed_frame(dut, batch0, batch1)
    results = await capture_serial_output(dut, N_DATA)
    assert_frame(results, batch0 + batch1)
    cocotb.log.info("Reset after a half frame realigns the buffer OK")


@cocotb.test()
async def test_clk_en_gating(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await reset_dut(dut)

    dut.i_en.value = 0
    await feed_batch(dut, [(99, -99)] * 8)
    for _ in range(30):
        await RisingEdge(dut.i_clk)
    dut.i_en.value = 1
    await RisingEdge(dut.i_clk)

    rng = random.Random(134)
    batch0 = random_batch(rng)
    batch1 = random_batch(rng)
    await feed_frame(dut, batch0, batch1)
    results = await capture_serial_output(dut, N_DATA)
    assert_frame(results, batch0 + batch1)
    cocotb.log.info("Batches fed while i_en was low are ignored OK")


@cocotb.test()
async def test_ready_returns_high_between_frames(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await reset_dut(dut)

    rng = random.Random(135)
    batch0 = random_batch(rng)
    batch1 = random_batch(rng)
    await feed_frame(dut, batch0, batch1)
    results = await capture_serial_output(dut, N_DATA)
    assert_frame(results, batch0 + batch1)

    for _ in range(60):
        await RisingEdge(dut.i_clk)
        if dut.o_ready.value == 1:
            break
    assert dut.o_ready.value == 1, "o_ready must return high after the frame"
    for _ in range(40):
        await RisingEdge(dut.i_clk)
        assert dut.o_data.value == 0, "the line must idle low between frames"
    cocotb.log.info("The link returns to idle between frames OK")


@cocotb.test()
async def test_alternating_patterns(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await reset_dut(dut)

    batch0 = [(-86, 85) for _ in range(8)]
    batch1 = [(85, -86) for _ in range(8)]
    await feed_frame(dut, batch0, batch1)
    results = await capture_serial_output(dut, N_DATA)
    assert_frame(results, batch0 + batch1)
    cocotb.log.info("Alternating bit patterns survive the serial link OK")


@cocotb.test()
async def test_long_random_run(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await reset_dut(dut)

    rng = random.Random(136)
    for frame in range(15):
        batch0 = random_batch(rng)
        batch1 = random_batch(rng)
        await feed_frame(dut, batch0, batch1)
        results = await capture_serial_output(dut, N_DATA)
        assert_frame(results, batch0 + batch1, f"frame {frame}: ")
    cocotb.log.info("15 random frames, 240 samples total OK")
