import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

CLK_NS = 20
DATA_WIDTH = 8
MASK = (1 << DATA_WIDTH) - 1
SYNC_DEPTH = 3


async def reset_dut(dut):
    dut.i_rstn.value = 0
    dut.i_trigger_n.value = 1
    dut.i_data.value = 0
    for _ in range(4):
        await RisingEdge(dut.i_clk)
    dut.i_rstn.value = 1
    await RisingEdge(dut.i_clk)


async def start(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await reset_dut(dut)


async def capture(dut, value, settle=6):
    dut.i_data.value = value & MASK
    await RisingEdge(dut.i_clk)
    dut.i_trigger_n.value = 0
    for _ in range(settle):
        await RisingEdge(dut.i_clk)
    dut.i_trigger_n.value = 1
    for _ in range(settle):
        await RisingEdge(dut.i_clk)
    return int(dut.o_data.value) & MASK


@cocotb.test()
async def test_reset_clears_output(dut):
    await start(dut)
    assert int(dut.o_data.value) == 0, "data_out must be zero after reset"
    dut.i_data.value = 0xA5
    got = await capture(dut, 0xA5)
    assert got == 0xA5
    dut.i_rstn.value = 0
    for _ in range(3):
        await RisingEdge(dut.i_clk)
    assert int(dut.o_data.value) == 0, "reset must clear the snapshot register"
    dut.i_rstn.value = 1
    await RisingEdge(dut.i_clk)
    cocotb.log.info("Reset clears the snapshot register OK")


@cocotb.test()
async def test_capture_on_falling_edge(dut):
    await start(dut)
    for value in [0x00, 0x01, 0x55, 0xAA, 0x7F, 0x80, 0xFE, 0xFF]:
        got = await capture(dut, value)
        assert got == value, f"expected 0x{value:02X}, got 0x{got:02X}"
    cocotb.log.info("Capture on every falling edge of the trigger OK")


@cocotb.test()
async def test_exhaustive_values(dut):
    await start(dut)
    for value in range(1 << DATA_WIDTH):
        got = await capture(dut, value, settle=4)
        assert got == value, f"expected 0x{value:02X}, got 0x{got:02X}"
    cocotb.log.info(f"All {1 << DATA_WIDTH} data values captured correctly OK")


@cocotb.test()
async def test_output_frozen_while_input_changes(dut):
    await start(dut)
    rng = random.Random(31)
    frozen = await capture(dut, 0x3C)
    assert frozen == 0x3C
    for _ in range(50):
        dut.i_data.value = rng.randint(0, MASK)
        await RisingEdge(dut.i_clk)
        assert int(dut.o_data.value) & MASK == frozen, (
            "data_out changed while the trigger was inactive"
        )
    cocotb.log.info("Snapshot stays frozen while data_in keeps changing OK")


@cocotb.test()
async def test_no_capture_on_rising_edge(dut):
    await start(dut)
    first = await capture(dut, 0x11)
    assert first == 0x11
    dut.i_trigger_n.value = 0
    for _ in range(4):
        await RisingEdge(dut.i_clk)
    dut.i_data.value = 0x22
    for _ in range(4):
        await RisingEdge(dut.i_clk)
    dut.i_trigger_n.value = 1
    for _ in range(6):
        await RisingEdge(dut.i_clk)
        assert int(dut.o_data.value) & MASK == 0x11, (
            "rising edge of the trigger must not capture"
        )
    cocotb.log.info("Only the falling edge captures OK")


@cocotb.test()
async def test_synchroniser_latency(dut):
    await start(dut)
    dut.i_data.value = 0x5A
    await RisingEdge(dut.i_clk)
    dut.i_trigger_n.value = 0
    for step in range(SYNC_DEPTH):
        await RisingEdge(dut.i_clk)
        assert int(dut.o_data.value) & MASK == 0, (
            f"capture happened after {step + 1} clocks, expected {SYNC_DEPTH}"
        )
    await RisingEdge(dut.i_clk)
    assert int(dut.o_data.value) & MASK == 0x5A, (
        "capture must land after the synchroniser depth"
    )
    dut.i_trigger_n.value = 1
    for _ in range(4):
        await RisingEdge(dut.i_clk)
    cocotb.log.info(f"Trigger passes through {SYNC_DEPTH} synchroniser stages OK")


@cocotb.test()
async def test_data_sampled_at_capture_time(dut):
    await start(dut)
    dut.i_data.value = 0xF0
    await RisingEdge(dut.i_clk)
    dut.i_trigger_n.value = 0
    await RisingEdge(dut.i_clk)
    dut.i_data.value = 0x0F
    for _ in range(6):
        await RisingEdge(dut.i_clk)
    got = int(dut.o_data.value) & MASK
    assert got == 0x0F, (
        f"the value present when the synchronised pulse fires must be captured, "
        f"got 0x{got:02X}"
    )
    dut.i_trigger_n.value = 1
    for _ in range(4):
        await RisingEdge(dut.i_clk)
    cocotb.log.info("Data is sampled when the synchronised pulse fires OK")


@cocotb.test()
async def test_repeated_triggers(dut):
    await start(dut)
    rng = random.Random(32)
    for _ in range(100):
        value = rng.randint(0, MASK)
        got = await capture(dut, value, settle=rng.randint(3, 8))
        assert got == value, f"expected 0x{value:02X}, got 0x{got:02X}"
    cocotb.log.info("100 repeated capture cycles OK")


@cocotb.test()
async def test_async_trigger_offset_from_clock(dut):
    await start(dut)
    rng = random.Random(33)
    for _ in range(40):
        value = rng.randint(0, MASK)
        dut.i_data.value = value
        await RisingEdge(dut.i_clk)
        await Timer(rng.randint(1, CLK_NS - 1), unit="ns")
        dut.i_trigger_n.value = 0
        for _ in range(6):
            await RisingEdge(dut.i_clk)
        got = int(dut.o_data.value) & MASK
        assert got == value, (
            f"asynchronous trigger missed: expected 0x{value:02X}, got 0x{got:02X}"
        )
        await Timer(rng.randint(1, CLK_NS - 1), unit="ns")
        dut.i_trigger_n.value = 1
        for _ in range(5):
            await RisingEdge(dut.i_clk)
    cocotb.log.info("Trigger edges asynchronous to the clock are captured OK")


@cocotb.test()
async def test_short_trigger_pulse(dut):
    await start(dut)
    baseline = await capture(dut, 0x21)
    assert baseline == 0x21
    dut.i_data.value = 0x77
    await RisingEdge(dut.i_clk)
    dut.i_trigger_n.value = 0
    await RisingEdge(dut.i_clk)
    dut.i_trigger_n.value = 1
    for _ in range(8):
        await RisingEdge(dut.i_clk)
    got = int(dut.o_data.value) & MASK
    assert got == 0x77, (
        f"a one-cycle trigger pulse must still capture, got 0x{got:02X}"
    )
    cocotb.log.info("Single-cycle trigger pulse captures OK")
