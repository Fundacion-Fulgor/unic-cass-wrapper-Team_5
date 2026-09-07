import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
import random

CLK_NS         = 20
NB_DATA        = 8
N_DATA         = 16
TIMEOUT_CYCLES = 200


def to_signed_8(val):
    val = val & 0xFF
    return val - 256 if val > 127 else val


async def reset_dut(dut):
    dut.i_rstn.value = 0
    dut.i_data.value  = 0
    for _ in range(4):
        await RisingEdge(dut.i_clk)
    dut.i_rstn.value = 1
    await RisingEdge(dut.i_clk)


async def drive_stream(dut, pairs):
    """
    Drives the start bit and then all data bits continuously,
    exactly one bit per clock cycle, without stopping.
    """
    # Start bit
    dut.i_data.value = 0
    await RisingEdge(dut.i_clk)
    dut.i_data.value = 1
    await RisingEdge(dut.i_clk)

    # Continuous data injection
    for re_val, im_val in pairs:
        word = ((re_val & 0xFF) << 8) | (im_val & 0xFF)
        for i in range(16):
            dut.i_data.value = (word >> (15 - i)) & 1
            await RisingEdge(dut.i_clk)
            
    # Return to 0 after the batch
    dut.i_data.value = 0


async def monitor_stream(dut, expected_samples):
    """
    Passively listens to the bus. Captures output whenever o_valid is 1.
    Finishes when the expected number of samples is collected.
    """
    results = []
    timeout_cnt = 0
    MAX_TIMEOUT = TIMEOUT_CYCLES * expected_samples

    while len(results) < expected_samples:
        await RisingEdge(dut.i_clk)
        timeout_cnt += 1
        
        if dut.o_valid.value == 1:
            results.append((
                to_signed_8(int(dut.o_data_re.value)),
                to_signed_8(int(dut.o_data_im.value))
            ))
            
        assert timeout_cnt < MAX_TIMEOUT, "Timeout: Did not receive all expected samples"
        
    return results


@cocotb.test()
async def test_basic_deserialization(dut):
    """
    Sends a full batch of N_DATA known IQ pairs and verifies each is
    correctly reconstructed by the RX serializer.
    """
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await reset_dut(dut)
    cocotb.log.info("--- test_basic_deserialization ---")

    pairs = [
        (0,    0   ), (127,  -128), (-1,   1   ), (85,   -86 ),
        (-50,  50  ), (127,  127 ), (-128, -128), (42,   -42 ),
        (1,    -1  ), (100,  -100), (0,    127 ), (-128, 0   ),
        (64,   -64 ), (-64,  64  ), (33,   -33 ), (99,   -99 ),
    ]

    cocotb.start_soon(drive_stream(dut, pairs))
    results = await monitor_stream(dut, N_DATA)

    for idx, ((re_val, im_val), (got_re, got_im)) in enumerate(zip(pairs, results)):
        exp_re = to_signed_8(re_val)
        exp_im = to_signed_8(im_val)
        assert got_re == exp_re and got_im == exp_im, \
            f"[{idx}] expected ({exp_re},{exp_im}), got ({got_re},{got_im})"
        cocotb.log.info(f"  [{idx:2d}] Re={got_re:+4d} Im={got_im:+4d}  OK")

    cocotb.log.info("test_basic_deserialization PASSED.")


@cocotb.test()
async def test_valid_single_pulse(dut):
    """
    Verifies that o_valid is asserted for exactly one clock cycle
    per received sample across a full batch.
    """
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await reset_dut(dut)
    cocotb.log.info("--- test_valid_single_pulse ---")

    pairs = [(i, -i) for i in range(N_DATA)]
    
    # Drive the stream in the background
    cocotb.start_soon(drive_stream(dut, pairs))
    
    valid_pulse_count = 0
    consecutive_valids = 0
    
    # Monitor for exactly the duration of the transmission + some buffer
    total_cycles_to_wait = (N_DATA * 2 * NB_DATA) + 10
    
    for _ in range(total_cycles_to_wait):
        await RisingEdge(dut.i_clk)
        if dut.o_valid.value == 1:
            valid_pulse_count += 1
            consecutive_valids += 1
            assert consecutive_valids <= 1, "o_valid was high for more than 1 consecutive cycle!"
        else:
            consecutive_valids = 0

    assert valid_pulse_count == N_DATA, \
        f"Expected exactly {N_DATA} valid pulses, got {valid_pulse_count}"
        
    cocotb.log.info(f"o_valid pulsed exactly 1 cycle per sample ({N_DATA} total pulses) OK")
    cocotb.log.info("test_valid_single_pulse PASSED.")


@cocotb.test()
async def test_consecutive_batches(dut):
    """
    Sends two full batches back to back and verifies the FSM resets
    correctly after N_DATA samples and starts listening for a new start bit.
    """
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await reset_dut(dut)
    cocotb.log.info("--- test_consecutive_batches ---")

    random.seed(42)
    MIN_VAL = -(1 << (NB_DATA - 1))
    MAX_VAL =  (1 << (NB_DATA - 1)) - 1

    for batch_idx in range(2):
        pairs = [(random.randint(MIN_VAL, MAX_VAL),
                  random.randint(MIN_VAL, MAX_VAL)) for _ in range(N_DATA)]

        cocotb.start_soon(drive_stream(dut, pairs))
        results = await monitor_stream(dut, N_DATA)

        for idx, ((re_val, im_val), (got_re, got_im)) in enumerate(zip(pairs, results)):
            exp_re = to_signed_8(re_val)
            exp_im = to_signed_8(im_val)
            assert got_re == exp_re and got_im == exp_im, \
                f"Batch {batch_idx}[{idx}]: expected ({exp_re},{exp_im}), got ({got_re},{got_im})"
            cocotb.log.info(f"  Batch {batch_idx}[{idx:2d}] Re={got_re:+4d} Im={got_im:+4d}  OK")

        # Wait a few cycles before next batch to simulate idle time
        for _ in range(5):
            await RisingEdge(dut.i_clk)

        cocotb.log.info(f"  Batch {batch_idx} PASSED.")

    cocotb.log.info("test_consecutive_batches PASSED.")


@cocotb.test()
async def test_spurious_then_valid(dut):
    """
    Sends a start bit followed by all-zero data (N_DATA samples),
    then sends a proper batch and verifies correct reception.
    """
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await reset_dut(dut)
    cocotb.log.info("--- test_spurious_then_valid ---")

    # First spurious batch
    spurious = [(0, 0)] * N_DATA
    cocotb.start_soon(drive_stream(dut, spurious))
    results = await monitor_stream(dut, N_DATA)

    for idx, (got_re, got_im) in enumerate(results):
        assert got_re == 0 and got_im == 0, \
            f"Spurious[{idx}]: expected (0,0), got ({got_re},{got_im})"

    cocotb.log.info("  Spurious batch received correctly (all zeros)  OK")

    # Idle time
    for _ in range(5):
        await RisingEdge(dut.i_clk)

    # Valid batch
    pairs = [(i * 7 - 64, i * 5 - 40) for i in range(N_DATA)]
    cocotb.start_soon(drive_stream(dut, pairs))
    results = await monitor_stream(dut, N_DATA)

    for idx, ((re_val, im_val), (got_re, got_im)) in enumerate(zip(pairs, results)):
        exp_re = to_signed_8(re_val)
        exp_im = to_signed_8(im_val)
        assert got_re == exp_re and got_im == exp_im, \
            f"[{idx}]: expected ({exp_re},{exp_im}), got ({got_re},{got_im})"
        cocotb.log.info(f"  [{idx:2d}] Re={got_re:+4d} Im={got_im:+4d}  OK")

    cocotb.log.info("test_spurious_then_valid PASSED.")

EXTREMES = [-128, -127, -1, 0, 1, 126, 127]


def random_pairs(rng, count=N_DATA):
    return [
        (rng.randint(-128, 127), rng.randint(-128, 127)) for _ in range(count)
    ]


async def send_and_check(dut, pairs, context=""):
    cocotb.start_soon(drive_stream(dut, pairs))
    results = await monitor_stream(dut, len(pairs))
    for idx, ((re_val, im_val), (got_re, got_im)) in enumerate(zip(pairs, results)):
        assert got_re == to_signed_8(re_val) and got_im == to_signed_8(im_val), (
            f"{context}[{idx}] expected "
            f"({to_signed_8(re_val)},{to_signed_8(im_val)}), got ({got_re},{got_im})"
        )
    return results


@cocotb.test()
async def test_extreme_values(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await reset_dut(dut)

    pairs = [
        (EXTREMES[i % 7], EXTREMES[(i * 3) % 7]) for i in range(N_DATA)
    ]
    await send_and_check(dut, pairs)
    cocotb.log.info("Full-scale signed values are deserialised correctly OK")


@cocotb.test()
async def test_many_consecutive_batches(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await reset_dut(dut)

    rng = random.Random(111)
    for batch in range(12):
        pairs = random_pairs(rng)
        await send_and_check(dut, pairs, f"batch {batch}: ")
        for _ in range(rng.randint(1, 12)):
            await RisingEdge(dut.i_clk)
    cocotb.log.info("12 consecutive batches with random idle gaps OK")


@cocotb.test()
async def test_no_gap_between_batches(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await reset_dut(dut)

    rng = random.Random(112)
    for batch in range(6):
        pairs = random_pairs(rng)
        await send_and_check(dut, pairs, f"batch {batch}: ")
    cocotb.log.info("Batches sent back to back with no idle time OK")


@cocotb.test()
async def test_all_ones_payload(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await reset_dut(dut)

    pairs = [(-1, -1)] * N_DATA
    await send_and_check(dut, pairs)
    cocotb.log.info("An all-ones payload does not retrigger the start detector OK")


@cocotb.test()
async def test_idle_low_produces_no_output(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await reset_dut(dut)

    dut.i_data.value = 0
    for _ in range(300):
        await RisingEdge(dut.i_clk)
        assert dut.o_valid.value == 0, "an idle low line must not produce samples"
    cocotb.log.info("A line held low never produces a sample OK")


@cocotb.test()
async def test_reception_after_long_idle(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await reset_dut(dut)

    rng = random.Random(113)
    await send_and_check(dut, random_pairs(rng), "first: ")

    dut.i_data.value = 0
    for _ in range(500):
        await RisingEdge(dut.i_clk)
        assert dut.o_valid.value == 0, "no samples expected during the idle gap"

    await send_and_check(dut, random_pairs(rng), "second: ")
    cocotb.log.info("Reception resumes after a long idle gap OK")


@cocotb.test()
async def test_reset_midframe(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await reset_dut(dut)

    dut.i_data.value = 0
    await RisingEdge(dut.i_clk)
    dut.i_data.value = 1
    for _ in range(40):
        await RisingEdge(dut.i_clk)
    await reset_dut(dut)
    assert dut.o_valid.value == 0, "reset must clear o_valid"

    rng = random.Random(114)
    pairs = random_pairs(rng)
    await send_and_check(dut, pairs)
    cocotb.log.info("Reset in the middle of a frame recovers cleanly OK")


@cocotb.test()
async def test_sample_counter_wraps(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await reset_dut(dut)

    rng = random.Random(115)
    total = 0
    for batch in range(5):
        pairs = random_pairs(rng)
        results = await send_and_check(dut, pairs, f"batch {batch}: ")
        assert len(results) == N_DATA, (
            f"batch {batch} produced {len(results)} samples instead of {N_DATA}"
        )
        total += len(results)
    assert total == 5 * N_DATA
    cocotb.log.info(f"Sample counter wraps correctly over {total} samples OK")


@cocotb.test()
async def test_valid_count_per_batch(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await reset_dut(dut)

    rng = random.Random(116)
    pairs = random_pairs(rng)
    sender = cocotb.start_soon(drive_stream(dut, pairs))

    pulses = 0
    for _ in range((N_DATA * 2 * NB_DATA) + 40):
        await RisingEdge(dut.i_clk)
        pulses += int(dut.o_valid.value)
    await sender
    assert pulses == N_DATA, (
        f"expected exactly {N_DATA} valid pulses in one batch, got {pulses}"
    )
    cocotb.log.info(f"Exactly {N_DATA} valid pulses per batch OK")


@cocotb.test()
async def test_alternating_bit_pattern(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await reset_dut(dut)

    pairs = [(-86 if i % 2 else 85, -86 if i % 2 else 85)
             for i in range(N_DATA)]
    await send_and_check(dut, pairs)
    cocotb.log.info("Alternating bit patterns deserialise without bit slips OK")


@cocotb.test()
async def test_long_random_stream(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await reset_dut(dut)

    rng = random.Random(117)
    for batch in range(25):
        pairs = random_pairs(rng)
        await send_and_check(dut, pairs, f"batch {batch}: ")
    cocotb.log.info("25 random batches, 400 samples total OK")
