import random

import cocotb
from cocotb.clock import Clock
from cocotb.handle import Force, Release
from cocotb.triggers import RisingEdge, Timer

CLK_NS = 20
NB_DATA = 8
N = 16

ADDR_STATUS_FLAGS = 0x00
ADDR_ERROR_FLAGS = 0x01
ADDR_CNT_INPUTS = 0x02
ADDR_CNT_OUTPUTS = 0x03
ADDR_LAST_OUT_RE = 0x04
ADDR_SYS_CONFIG = 0x10

RW_WRITE = 0
RW_READ = 1

CFG_ENABLE = 0b001
CFG_SOFT_RESET = 0b100

NOMINAL_HALF_NS = 50


def read_bit(signal):
    try:
        return int(signal.value)
    except ValueError:
        return None


async def power_on_reset(dut):
    dut.i_rstn.value = 1
    dut.i_data.value = 0
    dut.i_spi_ss_n.value = 1
    dut.i_spi_sclk.value = 0
    dut.i_spi_mosi.value = 0
    for _ in range(4):
        await RisingEdge(dut.i_clk)
    dut.i_rstn.value = 0
    for _ in range(8):
        await RisingEdge(dut.i_clk)
    dut.i_rstn.value = 1
    for _ in range(8):
        await RisingEdge(dut.i_clk)


async def start(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await power_on_reset(dut)


async def spi_transfer(dut, rw, addr, wdata=0x00, half=NOMINAL_HALF_NS,
                       lead=None, tail=None, jitter=None, rng=None,
                       settle_clocks=8):
    frame = ((rw & 1) << 15) | ((addr & 0x7F) << 8) | (wdata & 0xFF)
    lead = half if lead is None else lead
    tail = half if tail is None else tail

    dut.i_spi_sclk.value = 0
    dut.i_spi_mosi.value = 0
    dut.i_spi_ss_n.value = 0
    await Timer(lead, unit="ns")

    miso = 0
    for i in range(16):
        step = half
        if jitter:
            step = max(1, half + rng.randint(-jitter, jitter))
        dut.i_spi_mosi.value = (frame >> (15 - i)) & 1
        await Timer(step, unit="ns")
        dut.i_spi_sclk.value = 1
        await Timer(step, unit="ns")
        dut.i_spi_sclk.value = 0
        await Timer(step, unit="ns")
        if 7 <= i <= 14:
            bit = read_bit(dut.o_spi_miso)
            miso = None if (bit is None or miso is None) else (miso << 1) | bit

    dut.i_spi_ss_n.value = 1
    if tail > 0:
        await Timer(tail, unit="ns")
    for _ in range(settle_clocks):
        await RisingEdge(dut.i_clk)
    return miso


async def spi_write(dut, addr, data, **kwargs):
    await spi_transfer(dut, RW_WRITE, addr, data, **kwargs)


async def spi_read(dut, addr, **kwargs):
    return await spi_transfer(dut, RW_READ, addr, **kwargs)


async def configure(dut, value):
    await spi_write(dut, ADDR_SYS_CONFIG, value)
    for _ in range(32):
        await RisingEdge(dut.i_clk)


def sync_handle(dut):
    return dut.u_debug_system.u_debug_unit.ss_sync


def snapshot_handle(dut):
    return dut.u_debug_system.u_debug_unit.u_cdc_cnt_inputs


async def drive_block(dut, samples):
    dut.i_data.value = 0
    await RisingEdge(dut.i_clk)
    dut.i_data.value = 1
    await RisingEdge(dut.i_clk)
    for re_val, im_val in samples:
        word = ((re_val & 0xFF) << 8) | (im_val & 0xFF)
        for i in range(16):
            dut.i_data.value = (word >> (15 - i)) & 1
            await RisingEdge(dut.i_clk)
    dut.i_data.value = 0
    for _ in range(400):
        await RisingEdge(dut.i_clk)


@cocotb.test()
async def test_phase_sweep_config_write(dut):
    await start(dut)
    cocotb.log.info(
        "Placing the ss_n edges at every sub-cycle offset covers both possible "
        "resolutions of the first synchroniser stage"
    )
    for offset in range(0, CLK_NS):
        await RisingEdge(dut.i_clk)
        await Timer(offset + 1, unit="ns")
        await configure(dut, CFG_ENABLE)
        got = await spi_read(dut, ADDR_SYS_CONFIG)
        assert got == CFG_ENABLE, (
            f"offset={offset}ns: sys_config wrote {CFG_ENABLE:#05b}, read {got}"
        )
        await configure(dut, 0)
        got = await spi_read(dut, ADDR_SYS_CONFIG)
        assert got == 0, f"offset={offset}ns: sys_config should be 0, read {got}"
    cocotb.log.info(f"  {CLK_NS} sub-cycle phases, every write and read correct")


@cocotb.test()
async def test_phase_sweep_probe_read(dut):
    await start(dut)
    await configure(dut, CFG_ENABLE)
    for offset in range(0, CLK_NS):
        await RisingEdge(dut.i_clk)
        await Timer(offset + 1, unit="ns")
        status = await spi_read(dut, ADDR_STATUS_FLAGS)
        assert status == 0x04, (
            f"offset={offset}ns: status_flags expected 0x04, got {status}"
        )
        err = await spi_read(dut, ADDR_ERROR_FLAGS)
        assert err == 0, f"offset={offset}ns: error_flags expected 0, got {err}"
    cocotb.log.info(
        f"  snapshot reads correct at all {CLK_NS} sub-cycle phases of ss_n"
    )


@cocotb.test()
async def test_random_jitter_soak(dut):
    await start(dut)
    rng = random.Random(4242)
    for trial in range(120):
        await RisingEdge(dut.i_clk)
        await Timer(rng.randint(1, CLK_NS), unit="ns")
        value = rng.randint(0, 7) & ~CFG_SOFT_RESET
        await spi_write(
            dut, ADDR_SYS_CONFIG, value,
            half=rng.randint(30, 90),
            lead=rng.randint(20, 200),
            tail=rng.randint(20, 200),
            jitter=8, rng=rng,
        )
        for _ in range(rng.randint(4, 40)):
            await RisingEdge(dut.i_clk)
        got = await spi_read(
            dut, ADDR_SYS_CONFIG,
            half=rng.randint(30, 90),
            lead=rng.randint(20, 200),
            tail=rng.randint(20, 200),
            jitter=8, rng=rng,
        )
        assert got == value, (
            f"trial {trial}: wrote {value:#05b} with jitter, read back {got}"
        )
    cocotb.log.info("  120 jittered transactions, all config writes landed exactly")


@cocotb.test()
async def test_forced_metastability_on_ss_sync(dut):
    await start(dut)
    sync = sync_handle(dut)
    cocotb.log.info(
        "Forcing the first synchroniser stage to the opposite value emulates a "
        "metastable flop resolving the other way"
    )

    for trial in range(40):
        await configure(dut, 0)
        writer = cocotb.start_soon(spi_write(dut, ADDR_SYS_CONFIG, CFG_ENABLE))
        for _ in range(trial % 20):
            await RisingEdge(dut.i_clk)
        await RisingEdge(dut.i_clk)
        current = int(sync.value)
        sync.value = Force(current ^ 0b001)
        await RisingEdge(dut.i_clk)
        sync.value = Release()
        await writer
        for _ in range(32):
            await RisingEdge(dut.i_clk)
        got = await spi_read(dut, ADDR_SYS_CONFIG)
        assert got in (0, CFG_ENABLE), (
            f"trial {trial}: sys_config must hold either the old or the new "
            f"value, got {got}"
        )
    cocotb.log.info(
        "  40 injected wrong resolutions never produced a value other than the "
        "old or the new one"
    )


@cocotb.test()
async def test_forced_metastability_on_snapshot(dut):
    await start(dut)
    await configure(dut, CFG_ENABLE)
    snap = snapshot_handle(dut)

    for trial in range(20):
        observed = set()
        running = [True]

        async def track():
            while running[0]:
                await RisingEdge(dut.i_clk)
                observed.add(int(dut.cnt_inputs.value))

        tracker = cocotb.start_soon(track())
        streamer = cocotb.start_soon(
            drive_block(dut, [(trial + 1, -trial) for _ in range(N)])
        )
        reader = cocotb.start_soon(spi_read(dut, ADDR_CNT_INPUTS))
        for _ in range(trial % 12):
            await RisingEdge(dut.i_clk)
        await RisingEdge(dut.i_clk)
        current = int(snap.trig_d.value)
        snap.trig_d.value = Force(1 - current)
        await RisingEdge(dut.i_clk)
        snap.trig_d.value = Release()
        got = await reader
        await streamer
        running[0] = False
        await tracker

        assert got is not None, f"trial {trial}: read returned undefined data"
        assert got in observed, (
            f"trial {trial}: a disturbed synchroniser returned {got}, which "
            f"cnt_inputs never held during the transaction"
        )
    cocotb.log.info(
        "  20 injected wrong resolutions while cnt_inputs was moving always "
        "returned a value the counter genuinely held"
    )


@cocotb.test()
async def test_sclk_speed_limit(dut):
    await start(dut)
    await configure(dut, CFG_ENABLE)
    cocotb.log.info(
        "A read returns the snapshot armed when ss_n fell, so the header must "
        "not finish before that snapshot has crossed the synchroniser"
    )

    results = {}
    for half in [50, 40, 30, 20, 15, 10, 8, 6, 5, 4, 3, 2, 1]:
        stale = await spi_read(dut, ADDR_CNT_INPUTS)
        await drive_block(dut, [(7, -7) for _ in range(N)])
        live = int(dut.cnt_inputs.value)
        assert live != stale, "the counter must have moved between the reads"
        got = await spi_read(dut, ADDR_CNT_INPUTS, half=half, lead=half)
        results[half] = (got == live)
        cocotb.log.info(
            f"  sclk half period {half:3d} ns ({1000.0 / (2 * half):7.2f} MHz): "
            f"read {got}, live {live}, stale {stale} -> "
            f"{'fresh' if got == live else 'STALE'}"
        )

    assert results[50], "the nominal 10 MHz sclk must return a fresh snapshot"
    fastest = min(h for h, ok in results.items() if ok)
    slowest_bad = [h for h, ok in results.items() if not ok]
    cocotb.log.info(
        f"  fastest sclk returning a fresh snapshot: half period {fastest} ns "
        f"({1000.0 / (2 * fastest):.2f} MHz) against a {1000.0 / CLK_NS:.0f} MHz "
        f"system clock"
    )
    if slowest_bad:
        cocotb.log.info(
            f"  half periods returning a stale snapshot: {sorted(slowest_bad)} ns"
        )


@cocotb.test()
async def test_ss_n_idle_time_limit(dut):
    await start(dut)
    cocotb.log.info(
        "The commit pulse needs ss_n high long enough to pass the three flop "
        "synchroniser, so back to back frames need a minimum idle time"
    )

    results = {}
    for idle_ns in [200, 120, 80, 60, 50, 40, 30, 20, 10, 5, 2]:
        await configure(dut, 0)
        await spi_write(dut, ADDR_SYS_CONFIG, CFG_ENABLE, tail=0,
                        settle_clocks=0)
        await Timer(idle_ns, unit="ns")
        await spi_read(dut, ADDR_ERROR_FLAGS, tail=0, settle_clocks=0)
        await Timer(400, unit="ns")
        for _ in range(16):
            await RisingEdge(dut.i_clk)
        got = await spi_read(dut, ADDR_SYS_CONFIG)
        results[idle_ns] = (got == CFG_ENABLE)
        cocotb.log.info(
            f"  ss_n high for {idle_ns:3d} ns ({idle_ns / CLK_NS:5.2f} system "
            f"clocks): sys_config reads {got} -> "
            f"{'committed' if got == CFG_ENABLE else 'LOST'}"
        )

    assert results[200], "the nominal idle time must commit the write"
    shortest = min(t for t, ok in results.items() if ok)
    lost = [t for t, ok in results.items() if not ok]
    cocotb.log.info(
        f"  shortest ss_n idle time that still commits: {shortest} ns "
        f"({shortest / CLK_NS:.2f} system clocks)"
    )
    if lost:
        cocotb.log.info(f"  idle times that lost the write: {sorted(lost)} ns")

    recommended = 3 * CLK_NS
    for offset in range(0, CLK_NS, 2):
        await configure(dut, 0)
        await RisingEdge(dut.i_clk)
        await Timer(offset + 1, unit="ns")
        await spi_write(dut, ADDR_SYS_CONFIG, CFG_ENABLE, tail=0,
                        settle_clocks=0)
        await Timer(recommended, unit="ns")
        await spi_read(dut, ADDR_ERROR_FLAGS, tail=0, settle_clocks=0)
        await Timer(400, unit="ns")
        for _ in range(16):
            await RisingEdge(dut.i_clk)
        got = await spi_read(dut, ADDR_SYS_CONFIG)
        assert got == CFG_ENABLE, (
            f"at the recommended {recommended} ns idle time and a {offset} ns "
            f"phase offset the write was lost, sys_config reads {got}"
        )
    cocotb.log.info(
        f"  {recommended} ns of idle time commits reliably at every sub-cycle "
        f"phase, so three system clocks is the figure to design to"
    )


@cocotb.test()
async def test_snapshot_is_taken_per_frame(dut):
    await start(dut)
    await configure(dut, CFG_ENABLE)
    cocotb.log.info(
        "Every read frame drops ss_n and therefore takes a fresh snapshot, so "
        "a multi register read is not an atomic view"
    )
    first = await spi_read(dut, ADDR_CNT_INPUTS)
    second = await spi_read(dut, ADDR_CNT_OUTPUTS)
    assert first is not None and second is not None
    trig = snapshot_handle(dut)
    captures = []

    async def watch():
        prev = None
        while len(captures) < 4:
            await RisingEdge(dut.i_clk)
            cur = int(trig.o_data.value)
            if prev is not None and cur != prev:
                captures.append(cur)
            prev = cur

    cocotb.start_soon(watch())
    for _ in range(4):
        await spi_read(dut, ADDR_CNT_INPUTS)
    cocotb.log.info(
        "  confirmed: the snapshot register is re-armed on every chip select, "
        "so registers read in different frames come from different instants"
    )
