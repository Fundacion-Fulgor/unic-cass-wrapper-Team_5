import random

import cocotb
import numpy as np
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
from fft16 import FFT16

CLK_NS = 20
SPI_HALF_NS = 50
NB_DATA = 8
N = 16
START_TIMEOUT = 4000
DRAIN_CYCLES = 64
SETTLE_CYCLES = 20

ADDR_STATUS_FLAGS = 0x00
ADDR_ERROR_FLAGS = 0x01
ADDR_CNT_INPUTS = 0x02
ADDR_CNT_OUTPUTS = 0x03
ADDR_LAST_OUT_RE = 0x04
ADDR_LAST_OUT_IM = 0x05
ADDR_MID_DATA_RE = 0x06
ADDR_SYS_CONFIG = 0x10

PROBE_MAP = [
    ("status_flags", ADDR_STATUS_FLAGS),
    ("error_flags", ADDR_ERROR_FLAGS),
    ("cnt_inputs", ADDR_CNT_INPUTS),
    ("cnt_outputs", ADDR_CNT_OUTPUTS),
    ("last_out_re", ADDR_LAST_OUT_RE),
    ("last_out_im", ADDR_LAST_OUT_IM),
    ("mid_data_re", ADDR_MID_DATA_RE),
]

MAPPED_ADDRESSES = [addr for _, addr in PROBE_MAP] + [ADDR_SYS_CONFIG]
UNMAPPED_ADDRESSES = [0x07, 0x08, 0x0F, 0x11, 0x20, 0x3F, 0x55, 0x7F]

RW_WRITE = 0
RW_READ = 1

CFG_ENABLE = 0b001
CFG_INVERSE = 0b010
CFG_SOFT_RESET = 0b100

STATUS_RX_VALID = 0
STATUS_OUT_VALID = 1
STATUS_TX_READY = 2
STATUS_INVERSE = 3

NBF_TIME = 6
NBF_FREQ = 3

MDC_MAP = [0, 8, 1, 9, 2, 10, 3, 11, 4, 12, 5, 13, 6, 14, 7, 15]


def read_bit(signal):
    try:
        return int(signal.value)
    except ValueError:
        return None


def to_signed_8(value):
    value &= 0xFF
    return value - 256 if value > 127 else value


def formats(inverse):
    return (NBF_FREQ, NBF_TIME) if inverse else (NBF_TIME, NBF_FREQ)


def build_model(inverse):
    nbf_in, _ = formats(inverse)
    return FFT16(
        N=N, fxp=1, NB_INPUT=NB_DATA, NBF_INPUT=nbf_in, fft_mode=0 if inverse else 1
    )


def pack(value, nbf):
    return (
        int(round(value.real * (2 ** nbf))),
        int(round(value.imag * (2 ** nbf))),
    )


def quantise_block(model, values, nbf_in):
    return [model.round.crnd(v, True, NB_DATA, nbf_in, "around") for v in values]


def random_block(model, nbf_in, seed):
    np.random.seed(seed)
    raw = 2 * np.random.uniform(-1, 1, N) + 2j * np.random.uniform(-1, 1, N)
    return quantise_block(model, raw, nbf_in)


def expected_serial(model, input_q, nbf_out):
    bins = model.process(input_q)
    return [pack(bins[MDC_MAP[phys]], nbf_out) for phys in range(N)]


# ---------------------------------------------------------------------------
# SPI master
# ---------------------------------------------------------------------------


async def spi_transfer(dut, rw, addr, wdata=0x00):
    frame = ((rw & 1) << 15) | ((addr & 0x7F) << 8) | (wdata & 0xFF)
    dut.i_spi_ss_n.value = 0
    dut.i_spi_sclk.value = 0
    dut.i_spi_mosi.value = 0
    await Timer(SPI_HALF_NS, unit="ns")
    miso = 0
    for i in range(16):
        dut.i_spi_mosi.value = (frame >> (15 - i)) & 1
        await Timer(SPI_HALF_NS, unit="ns")
        dut.i_spi_sclk.value = 1
        await Timer(SPI_HALF_NS, unit="ns")
        dut.i_spi_sclk.value = 0
        await Timer(SPI_HALF_NS, unit="ns")
        if 7 <= i <= 14:
            bit = read_bit(dut.o_spi_miso)
            miso = None if (bit is None or miso is None) else (miso << 1) | bit
    dut.i_spi_ss_n.value = 1
    await Timer(SPI_HALF_NS, unit="ns")
    for _ in range(8):
        await RisingEdge(dut.i_clk)
    return miso


async def spi_write(dut, addr, data):
    await spi_transfer(dut, RW_WRITE, addr, data)


async def spi_read(dut, addr):
    return await spi_transfer(dut, RW_READ, addr)


async def spi_abort(dut, n_bits, pattern=0xFFFF):
    dut.i_spi_ss_n.value = 0
    dut.i_spi_sclk.value = 0
    await Timer(SPI_HALF_NS, unit="ns")
    for i in range(n_bits):
        dut.i_spi_mosi.value = (pattern >> (15 - i)) & 1
        await Timer(SPI_HALF_NS, unit="ns")
        dut.i_spi_sclk.value = 1
        await Timer(SPI_HALF_NS, unit="ns")
        dut.i_spi_sclk.value = 0
        await Timer(SPI_HALF_NS, unit="ns")
    dut.i_spi_ss_n.value = 1
    await Timer(SPI_HALF_NS, unit="ns")
    for _ in range(8):
        await RisingEdge(dut.i_clk)


async def read_all_probes(dut):
    return {name: await spi_read(dut, addr) for name, addr in PROBE_MAP}


# ---------------------------------------------------------------------------
# Chip control
# ---------------------------------------------------------------------------


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


async def set_config(dut, enable, inverse, drain=DRAIN_CYCLES):
    value = (CFG_ENABLE if enable else 0) | (CFG_INVERSE if inverse else 0)
    await spi_write(dut, ADDR_SYS_CONFIG, value)
    for _ in range(drain):
        await RisingEdge(dut.i_clk)
    return value


async def soft_reset(dut, enable=True, inverse=False):
    await spi_write(dut, ADDR_SYS_CONFIG, CFG_SOFT_RESET)
    for _ in range(16):
        await RisingEdge(dut.i_clk)
    return await set_config(dut, enable, inverse)


async def bring_up(dut, inverse=False):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await power_on_reset(dut)
    await soft_reset(dut, enable=False, inverse=False)
    await set_config(dut, enable=True, inverse=inverse)


# ---------------------------------------------------------------------------
# Serial link
# ---------------------------------------------------------------------------


async def drive_stream(dut, samples):
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


async def capture_block(dut, n_samples=N):
    results = []
    for idx in range(n_samples):
        if idx == 0:
            for _ in range(START_TIMEOUT):
                await RisingEdge(dut.i_clk)
                if int(dut.o_data.value) == 1:
                    break
            else:
                assert False, "Timeout: no start bit seen on o_data"
        else:
            await RisingEdge(dut.i_clk)
            await RisingEdge(dut.i_clk)
        word = 0
        for _ in range(16):
            await RisingEdge(dut.i_clk)
            word = (word << 1) | int(dut.o_data.value)
        results.append((to_signed_8(word >> 8), to_signed_8(word & 0xFF)))
    return results


async def transfer_block(dut, input_q, nbf_in):
    samples = [pack(x, nbf_in) for x in input_q]
    send = cocotb.start_soon(drive_stream(dut, samples))
    received = await capture_block(dut)
    await send
    return received


async def run_verified_block(dut, inverse, seed, label=""):
    nbf_in, nbf_out = formats(inverse)
    model = build_model(inverse)
    input_q = random_block(model, nbf_in, seed)
    expected = expected_serial(model, input_q, nbf_out)
    received = await transfer_block(dut, input_q, nbf_in)
    mode = "IFFT" if inverse else "FFT"
    for phys in range(N):
        assert received[phys] == expected[phys], (
            f"{label}{mode} seed={seed} sample {phys} (bin {MDC_MAP[phys]}): "
            f"expected {expected[phys]}, got {received[phys]}"
        )
    return received


async def idle(dut, cycles=SETTLE_CYCLES):
    for _ in range(cycles):
        await RisingEdge(dut.i_clk)


def expected_idle_status(inverse):
    return (1 << STATUS_TX_READY) | ((1 << STATUS_INVERSE) if inverse else 0)


async def check_idle_status(dut, inverse, label=""):
    status = await spi_read(dut, ADDR_STATUS_FLAGS)
    expected = expected_idle_status(inverse)
    assert status == expected, (
        f"{label}status_flags expected 0x{expected:02X}, got 0x{status:02X}"
    )
    return status


async def check_counters(dut, expect_in, expect_out, label=""):
    cnt_in = await spi_read(dut, ADDR_CNT_INPUTS)
    cnt_out = await spi_read(dut, ADDR_CNT_OUTPUTS)
    assert cnt_in == expect_in % 256, (
        f"{label}cnt_inputs expected {expect_in % 256}, got {cnt_in}"
    )
    assert cnt_out == expect_out % 256, (
        f"{label}cnt_outputs expected {expect_out % 256}, got {cnt_out}"
    )
    return cnt_in, cnt_out


async def check_last_out(dut, received, label=""):
    last_re = to_signed_8(await spi_read(dut, ADDR_LAST_OUT_RE))
    last_im = to_signed_8(await spi_read(dut, ADDR_LAST_OUT_IM))
    assert (last_re, last_im) == received[-1], (
        f"{label}last_out expected {received[-1]}, got {(last_re, last_im)}"
    )
    return last_re, last_im


# ---------------------------------------------------------------------------
# Bring-up sequence
# ---------------------------------------------------------------------------


@cocotb.test()
async def test_bringup_01_power_on_state(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    cocotb.log.info("STEP 1: release reset and inspect the register map")
    await power_on_reset(dut)

    config = await spi_read(dut, ADDR_SYS_CONFIG)
    assert config == 0, f"sys_config must power up at 0, got 0x{config:02X}"

    expected_probes = {
        "status_flags": expected_idle_status(False),
        "error_flags": 0,
        "cnt_inputs": 0,
        "cnt_outputs": 0,
        "last_out_re": 0,
        "last_out_im": 0,
    }
    probes = await read_all_probes(dut)
    for name, want in expected_probes.items():
        assert probes[name] == want, (
            f"{name} must power up at 0x{want:02X}, got {probes[name]}"
        )
    cocotb.log.info(
        f"  reset register map matches: "
        f"{ {k: f'0x{v:02X}' for k, v in expected_probes.items()} }"
    )
    cocotb.log.info(
        "  status_flags reads 0x04 because tx_ready is high while the "
        "transmitter is idle"
    )

    assert probes["mid_data_re"] is None, (
        "mid_data_re probes the radix-4 delay line, which carries no reset, so "
        f"it is expected to be undefined before any data arrives, got "
        f"{probes['mid_data_re']}"
    )
    cocotb.log.info(
        "  mid_data_re is undefined until the delay line fills, as expected for "
        "a probe into an unreset datapath"
    )

    for addr in UNMAPPED_ADDRESSES:
        value = await spi_read(dut, addr)
        assert value == 0, f"unmapped 0x{addr:02X} must read 0, got {value}"
    cocotb.log.info(f"  {len(UNMAPPED_ADDRESSES)} unmapped addresses read 0")

    cocotb.log.info("STEP 2: the serial output must stay idle with no stimulus")
    for _ in range(1000):
        await RisingEdge(dut.i_clk)
        assert int(dut.o_data.value) == 0, "o_data toggled with no input"
    assert int(dut.o_spi_miso.value) == 0, "miso must idle low while deselected"
    cocotb.log.info("  o_data and o_spi_miso idle low for 1000 cycles")

    cocotb.log.info("STEP 3: mid_data_re becomes defined once a block has flowed")
    await set_config(dut, enable=True, inverse=False)
    await run_verified_block(dut, inverse=False, seed=1000)
    await idle(dut)
    mid = await spi_read(dut, ADDR_MID_DATA_RE)
    assert mid is not None, "mid_data_re must be defined after a block"
    cocotb.log.info(f"  mid_data_re now reads {to_signed_8(mid)}")
    cocotb.log.info("test_bringup_01_power_on_state PASSED")


@cocotb.test()
async def test_bringup_02_disabled_core_blocks_data(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await power_on_reset(dut)
    cocotb.log.info("STEP 1: leave the core disabled and inject a full block")

    model = build_model(False)
    input_q = random_block(model, NBF_TIME, 1001)
    await drive_stream(dut, [pack(x, NBF_TIME) for x in input_q])

    cocotb.log.info("STEP 2: the receiver still counts, the core emits nothing")
    for _ in range(600):
        await RisingEdge(dut.i_clk)
        assert int(dut.o_data.value) == 0, "o_data active while the core is disabled"

    await idle(dut)
    await check_counters(dut, N, 0, "disabled: ")
    err = await spi_read(dut, ADDR_ERROR_FLAGS)
    assert err == 0, f"error_flags must stay clear, got 0x{err:02X}"
    cocotb.log.info("  cnt_inputs=16 cnt_outputs=0 error_flags=0x00")

    cocotb.log.info("STEP 3: enabling the core does not clear the counters")
    await set_config(dut, enable=True, inverse=False)
    await check_counters(dut, N, 0, "after enable: ")

    cocotb.log.info("STEP 4: the first enabled block comes out correct")
    received = await run_verified_block(dut, inverse=False, seed=1002)
    await idle(dut)
    await check_counters(dut, 2 * N, N, "after first enabled block: ")
    cocotb.log.info(f"  first block after enable matches the model: {received[0]}")
    cocotb.log.info("test_bringup_02_disabled_core_blocks_data PASSED")


@cocotb.test()
async def test_bringup_03_configuration_register(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await power_on_reset(dut)
    cocotb.log.info("STEP 1: every sys_config value reads back")

    for value in range(8):
        await spi_write(dut, ADDR_SYS_CONFIG, value)
        await idle(dut, 8)
        got = await spi_read(dut, ADDR_SYS_CONFIG)
        assert got == value, (
            f"sys_config wrote {value:#05b}, read back {got:#05b}"
        )
    cocotb.log.info("  all 8 configuration values written and read back")

    cocotb.log.info("STEP 2: the upper write bits are ignored")
    for value in [0xF8, 0xFD, 0xAA, 0xFF]:
        await spi_write(dut, ADDR_SYS_CONFIG, value)
        await idle(dut, 8)
        got = await spi_read(dut, ADDR_SYS_CONFIG)
        assert got == (value & 0b111), (
            f"wrote 0x{value:02X}, expected {value & 0b111:#05b}, got {got:#05b}"
        )

    cocotb.log.info("STEP 3: writes to probe addresses must not change the config")
    await soft_reset(dut, enable=True, inverse=False)
    for _, addr in PROBE_MAP:
        await spi_write(dut, addr, 0b111)
        got = await spi_read(dut, ADDR_SYS_CONFIG)
        assert got == CFG_ENABLE, (
            f"a write to 0x{addr:02X} changed sys_config to {got:#05b}"
        )
    cocotb.log.info("  the probe registers are read-only")

    cocotb.log.info("STEP 4: the inverse bit is observable in status_flags")
    await set_config(dut, enable=True, inverse=False)
    await check_idle_status(dut, inverse=False, label="fft: ")
    await set_config(dut, enable=True, inverse=True)
    await check_idle_status(dut, inverse=True, label="ifft: ")
    cocotb.log.info("test_bringup_03_configuration_register PASSED")


@cocotb.test()
async def test_bringup_04_first_fft_block(dut):
    await bring_up(dut, inverse=False)
    cocotb.log.info("STEP 1: run one FFT block and check it against the model")

    received = await run_verified_block(dut, inverse=False, seed=2001)
    await idle(dut)
    cocotb.log.info(f"  16 samples match the fixed-point model, last={received[-1]}")

    cocotb.log.info("STEP 2: cross-check every debug register")
    await check_counters(dut, N, N, "fft: ")
    await check_idle_status(dut, inverse=False, label="fft: ")
    await check_last_out(dut, received, "fft: ")
    err = await spi_read(dut, ADDR_ERROR_FLAGS)
    assert err == 0, f"a mid-scale block must not clip, error_flags=0x{err:02X}"

    model = build_model(False)
    input_q = random_block(model, NBF_TIME, 2001)
    injected = [re for re, _ in (pack(x, NBF_TIME) for x in input_q)]
    mid = to_signed_8(await spi_read(dut, ADDR_MID_DATA_RE))
    assert mid in injected, (
        f"mid_data_re={mid} is not one of the injected real values"
    )
    cocotb.log.info(f"  counters, status, last_out, error_flags and mid_data_re OK")
    cocotb.log.info("test_bringup_04_first_fft_block PASSED")


@cocotb.test()
async def test_bringup_05_first_ifft_block(dut):
    await bring_up(dut, inverse=True)
    cocotb.log.info("STEP 1: run one IFFT block and check it against the model")

    received = await run_verified_block(dut, inverse=True, seed=2002)
    await idle(dut)
    cocotb.log.info(f"  16 samples match the fixed-point model, last={received[-1]}")

    cocotb.log.info("STEP 2: cross-check every debug register")
    await check_counters(dut, N, N, "ifft: ")
    await check_idle_status(dut, inverse=True, label="ifft: ")
    await check_last_out(dut, received, "ifft: ")
    err = await spi_read(dut, ADDR_ERROR_FLAGS)
    assert err == 0, f"a mid-scale block must not clip, error_flags=0x{err:02X}"
    cocotb.log.info("test_bringup_05_first_ifft_block PASSED")


@cocotb.test()
async def test_bringup_06_long_mixed_session(dut):
    await bring_up(dut, inverse=False)
    cocotb.log.info("STEP 1: run a long session that switches transform mid-stream")

    schedule = [
        (False, 3),
        (True, 2),
        (False, 1),
        (True, 3),
        (False, 2),
        (True, 1),
        (False, 3),
        (True, 2),
    ]

    current = False
    total = 0
    seed = 3000

    for inverse, count in schedule:
        if inverse != current:
            await set_config(dut, enable=True, inverse=inverse, drain=16)
            current = inverse
            cocotb.log.info(
                f"  switched to {'IFFT' if inverse else 'FFT'} with a plain "
                f"sys_config write, no reset"
            )
            await check_idle_status(dut, inverse, "after switch: ")
        for _ in range(count):
            seed += 1
            received = await run_verified_block(
                dut, inverse, seed, f"block {total}: "
            )
            total += 1
            await idle(dut)
            await check_counters(
                dut, total * N, total * N, f"block {total - 1}: "
            )
            await check_last_out(dut, received, f"block {total - 1}: ")
            await check_idle_status(dut, inverse, f"block {total - 1}: ")

    cocotb.log.info(
        f"STEP 2: {total} blocks across {len(schedule)} mode changes, "
        f"{total * N} samples, all verified against the model"
    )
    assert total == sum(c for _, c in schedule)
    cocotb.log.info("test_bringup_06_long_mixed_session PASSED")


@cocotb.test()
async def test_bringup_07_debug_access_during_streaming(dut):
    await bring_up(dut, inverse=False)
    cocotb.log.info("STEP 1: hammer the SPI port while blocks are streaming")

    samples_seen = []
    running = [True]

    async def probe_loop():
        while running[0]:
            for _, addr in PROBE_MAP:
                if not running[0]:
                    return
                value = await spi_read(dut, addr)
                samples_seen.append((addr, value))
                assert 0 <= value <= 0xFF

    probe = cocotb.start_soon(probe_loop())

    for idx in range(4):
        await run_verified_block(dut, inverse=False, seed=4000 + idx, label=f"b{idx}: ")

    running[0] = False
    await probe

    assert len(samples_seen) >= 2 * len(PROBE_MAP), (
        f"expected sustained SPI traffic, only {len(samples_seen)} reads happened"
    )
    cocotb.log.info(
        f"  {len(samples_seen)} SPI reads during 4 verified blocks, "
        f"data path unaffected"
    )

    cocotb.log.info("STEP 2: the counters survived the concurrent access")
    await idle(dut)
    await check_counters(dut, 4 * N, 4 * N, "concurrent: ")
    cocotb.log.info("test_bringup_07_debug_access_during_streaming PASSED")


@cocotb.test()
async def test_bringup_08_error_flag_lifecycle(dut):
    await bring_up(dut, inverse=False)
    cocotb.log.info("STEP 1: a mid-scale block leaves the error flag clear")

    await run_verified_block(dut, inverse=False, seed=5001)
    await idle(dut)
    err = await spi_read(dut, ADDR_ERROR_FLAGS)
    assert err == 0, f"error_flags must start clear, got 0x{err:02X}"

    cocotb.log.info("STEP 2: a full-scale block drives the output into saturation")
    await transfer_block(dut, [complex(127 / 64.0, 127 / 64.0)] * N, NBF_TIME)
    await idle(dut)
    err = await spi_read(dut, ADDR_ERROR_FLAGS)
    assert err & 0x01, (
        f"error_flags[0] must latch on a saturating block, got 0x{err:02X}"
    )
    cocotb.log.info(f"  error_flags=0x{err:02X} after saturation")

    cocotb.log.info("STEP 3: the flag is sticky until a reset")
    await run_verified_block(dut, inverse=False, seed=5002)
    await idle(dut)
    err = await spi_read(dut, ADDR_ERROR_FLAGS)
    assert err & 0x01, "error_flags[0] must stay latched until a reset"

    cocotb.log.info("STEP 4: a soft reset clears it and the core keeps working")
    await soft_reset(dut, enable=True, inverse=False)
    err = await spi_read(dut, ADDR_ERROR_FLAGS)
    assert err == 0, f"a soft reset must clear error_flags, got 0x{err:02X}"
    await check_counters(dut, 0, 0, "after soft reset: ")
    await run_verified_block(dut, inverse=False, seed=5003)
    await idle(dut)
    err = await spi_read(dut, ADDR_ERROR_FLAGS)
    assert err == 0, f"error_flags must stay clear, got 0x{err:02X}"
    cocotb.log.info("test_bringup_08_error_flag_lifecycle PASSED")


@cocotb.test()
async def test_bringup_09_spi_abort_robustness(dut):
    await bring_up(dut, inverse=False)
    cocotb.log.info("STEP 1: abort SPI frames of every length between good ones")

    rng = random.Random(6001)
    for n_bits in range(1, 16):
        await spi_write(dut, ADDR_SYS_CONFIG, CFG_ENABLE)
        await idle(dut, 8)
        await spi_abort(dut, n_bits, rng.randint(0, 0xFFFF))
        config = await spi_read(dut, ADDR_SYS_CONFIG)
        assert config == CFG_ENABLE, (
            f"a {n_bits}-bit aborted frame changed sys_config to {config:#05b}"
        )
        value = await spi_read(dut, ADDR_CNT_INPUTS)
        assert 0 <= value <= 0xFF
    cocotb.log.info("  15 aborted frames left the configuration untouched")

    cocotb.log.info("STEP 2: many read frames after aborts never forge a write")
    for _ in range(60):
        await spi_abort(dut, rng.randint(1, 15), rng.randint(0, 0xFFFF))
        await spi_read(dut, rng.choice(MAPPED_ADDRESSES))
        config = await spi_read(dut, ADDR_SYS_CONFIG)
        assert config == CFG_ENABLE, (
            f"a read frame after an abort changed sys_config to {config:#05b}"
        )

    cocotb.log.info("STEP 3: the data path still works after all that")
    await soft_reset(dut, enable=True, inverse=False)
    await run_verified_block(dut, inverse=False, seed=6002)
    cocotb.log.info("test_bringup_09_spi_abort_robustness PASSED")


@cocotb.test()
async def test_bringup_10_reset_matrix(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    cocotb.log.info("STEP 1: a hard reset before every block")

    for idx in range(3):
        await power_on_reset(dut)
        await set_config(dut, enable=True, inverse=bool(idx % 2))
        await run_verified_block(dut, bool(idx % 2), 7000 + idx, f"hard {idx}: ")
        await idle(dut)
        await check_counters(dut, N, N, f"hard {idx}: ")
    cocotb.log.info("  3 blocks after hard resets")

    cocotb.log.info("STEP 2: a soft reset before every block")
    for idx in range(3):
        await soft_reset(dut, enable=True, inverse=bool(idx % 2))
        await check_counters(dut, 0, 0, f"soft {idx}: ")
        await run_verified_block(dut, bool(idx % 2), 7100 + idx, f"soft {idx}: ")
        await idle(dut)
        await check_counters(dut, N, N, f"soft {idx}: ")
    cocotb.log.info("  3 blocks after soft resets")

    cocotb.log.info("STEP 3: disable and re-enable without any reset")
    for idx in range(3):
        await set_config(dut, enable=False, inverse=False, drain=16)
        await set_config(dut, enable=True, inverse=False)
        await run_verified_block(dut, False, 7200 + idx, f"gated {idx}: ")
    cocotb.log.info("  3 blocks after gating the core off and on")
    cocotb.log.info("test_bringup_10_reset_matrix PASSED")


@cocotb.test()
async def test_bringup_11_sustained_throughput(dut):
    await bring_up(dut, inverse=False)
    cocotb.log.info("STEP 1: stream 20 blocks back to back with no reset")

    total = 0
    for idx in range(20):
        received = await run_verified_block(dut, False, 8000 + idx, f"blk {idx}: ")
        total += 1
        if idx % 5 == 4:
            await idle(dut)
            await check_counters(dut, total * N, total * N, f"blk {idx}: ")
            await check_last_out(dut, received, f"blk {idx}: ")
    cocotb.log.info(f"  {total} blocks, {total * N} samples, all verified")

    cocotb.log.info("STEP 2: keep going until the 8-bit counters wrap")
    while total * N < 300:
        await run_verified_block(dut, False, 8100 + total, f"wrap {total}: ")
        total += 1
    await idle(dut)
    cnt_in, cnt_out = await check_counters(dut, total * N, total * N, "wrapped: ")
    assert total * N > 256, "the counters were expected to wrap"
    cocotb.log.info(
        f"  {total} blocks total, {total * N} samples, counters wrapped to "
        f"{cnt_in}/{cnt_out}"
    )
    cocotb.log.info("test_bringup_11_sustained_throughput PASSED")


@cocotb.test()
async def test_bringup_12_structural_signals(dut):
    await bring_up(dut, inverse=False)
    cocotb.log.info("STEP 1: a constant block puts all the energy in bin 0")

    amplitude = 4
    received = await transfer_block(
        dut, [complex(amplitude / 64.0, 0)] * N, NBF_TIME
    )
    non_zero = [(idx, val) for idx, val in enumerate(received) if val != (0, 0)]
    assert len(non_zero) == 1 and non_zero[0][0] == 0, (
        f"a constant input must excite only bin 0, got {non_zero}"
    )
    cocotb.log.info(f"  bin 0 = {non_zero[0][1]}, every other bin is zero")

    cocotb.log.info("STEP 2: an impulse gives a flat spectrum")
    samples = [complex(0, 0)] * N
    samples[0] = complex(1.0, 0)
    received = await transfer_block(dut, samples, NBF_TIME)
    assert all(val == received[0] for val in received), (
        f"an impulse must give a flat spectrum, got {received}"
    )
    assert received[0] != (0, 0), "the flat spectrum must be non-zero"
    cocotb.log.info(f"  all 16 bins equal {received[0]}")

    cocotb.log.info("STEP 3: half-scale tones land in the expected bin")
    for k in [1, 2, 3, 5, 7]:
        tone = [
            complex(
                0.5 * float(np.cos(2 * np.pi * k * n / N)),
                0.5 * float(np.sin(2 * np.pi * k * n / N)),
            )
            for n in range(N)
        ]
        received = await transfer_block(dut, tone, NBF_TIME)
        magnitudes = [0.0] * N
        for phys in range(N):
            re, im = received[phys]
            magnitudes[MDC_MAP[phys]] = (re * re + im * im) ** 0.5
        peak = max(range(N), key=lambda i: magnitudes[i])
        assert peak == k, f"tone k={k} peaked at bin {peak}: {magnitudes}"
        for idx in range(N):
            if idx != k:
                assert magnitudes[idx] <= 3.0, (
                    f"tone k={k} leaked {magnitudes[idx]:.2f} into bin {idx}"
                )
        cocotb.log.info(f"  tone k={k} peaks at bin {peak} with |X|={magnitudes[k]:.1f}")

    await idle(dut)
    err = await spi_read(dut, ADDR_ERROR_FLAGS)
    assert err == 0, f"half-scale tones must not clip, error_flags=0x{err:02X}"
    cocotb.log.info("  no clipping reported for half-scale tones")

    cocotb.log.info("STEP 4: a full-scale tone exceeds the output range")
    tone = [
        complex(
            float(np.cos(2 * np.pi * 3 * n / N)),
            float(np.sin(2 * np.pi * 3 * n / N)),
        )
        for n in range(N)
    ]
    received = await transfer_block(dut, tone, NBF_TIME)
    peak_sample = received[MDC_MAP.index(3)]
    assert 127 in peak_sample or -128 in peak_sample, (
        f"a full-scale tone should saturate bin 3, got {peak_sample}"
    )
    await idle(dut)
    err = await spi_read(dut, ADDR_ERROR_FLAGS)
    assert err & 0x01, (
        f"saturation must latch error_flags[0], got 0x{err:02X}"
    )
    cocotb.log.info(
        f"  bin 3 saturated at {peak_sample} and error_flags=0x{err:02X}; "
        f"the useful input range for a single tone is half scale"
    )

    cocotb.log.info("STEP 5: after a soft reset an all-zero block is clean")
    await soft_reset(dut, enable=True, inverse=False)
    received = await transfer_block(dut, [complex(0, 0)] * N, NBF_TIME)
    assert all(val == (0, 0) for val in received), f"expected zeros, got {received}"
    await idle(dut)
    err = await spi_read(dut, ADDR_ERROR_FLAGS)
    assert err == 0, f"a soft reset must clear error_flags, got 0x{err:02X}"
    cocotb.log.info("test_bringup_12_structural_signals PASSED")


MIN_PAIR_GAP = 18
SAFE_BLOCK_GAP = 32
INPUT_FRAME_CYCLES = 258
READOUT_CYCLES = 274


async def stream_two_blocks(dut, blocks, nbf_in, gap):
    async def sender():
        await drive_stream(dut, [pack(x, nbf_in) for x in blocks[0]])
        for _ in range(gap):
            await RisingEdge(dut.i_clk)
        await drive_stream(dut, [pack(x, nbf_in) for x in blocks[1]])

    send = cocotb.start_soon(sender())
    first = await capture_block(dut)
    second = await capture_block(dut)
    await send
    return first, second


async def stream_many_blocks(dut, payloads, nbf_in, gap):
    async def sender():
        for idx, payload in enumerate(payloads):
            await drive_stream(dut, [pack(x, nbf_in) for x in payload])
            if idx < len(payloads) - 1:
                for _ in range(gap):
                    await RisingEdge(dut.i_clk)

    send = cocotb.start_soon(sender())
    received = [await capture_block(dut) for _ in range(len(payloads))]
    await send
    return received


@cocotb.test()
async def test_bringup_13_block_pacing(dut):
    await bring_up(dut, inverse=False)
    cocotb.log.info(
        f"STEP 1: the output frame takes {READOUT_CYCLES} clocks while the "
        f"input frame takes {INPUT_FRAME_CYCLES}, so the host must pace blocks"
    )

    nbf_in, nbf_out = formats(False)
    model = build_model(False)
    blocks = [random_block(model, nbf_in, 9000 + idx) for idx in range(2)]
    expected = [expected_serial(model, block, nbf_out) for block in blocks]

    for gap in [MIN_PAIR_GAP, 24, SAFE_BLOCK_GAP, 64, 256]:
        await bring_up(dut, inverse=False)
        first, second = await stream_two_blocks(dut, blocks, nbf_in, gap)
        assert first == expected[0], f"gap={gap}: first block corrupted"
        assert second == expected[1], f"gap={gap}: second block corrupted"
        cocotb.log.info(f"  gap={gap:3d} cycles: two consecutive blocks correct")

    cocotb.log.info(
        f"STEP 2: {MIN_PAIR_GAP} clocks is the tightest spacing that still "
        f"works for a pair, and it leaves no margin"
    )

    cocotb.log.info(
        f"STEP 3: sustained streaming at the qualified {SAFE_BLOCK_GAP}-clock gap"
    )
    await bring_up(dut, inverse=False)
    seeds = list(range(9100, 9120))
    models = [build_model(False) for _ in seeds]
    payloads = [random_block(m, nbf_in, s) for m, s in zip(models, seeds)]
    wanted = [expected_serial(m, b, nbf_out) for m, b in zip(models, payloads)]

    received = await stream_many_blocks(dut, payloads, nbf_in, SAFE_BLOCK_GAP)
    for idx, (got, want) in enumerate(zip(received, wanted)):
        assert got == want, (
            f"sustained block {idx} at a {SAFE_BLOCK_GAP}-clock gap: "
            f"expected {want}, got {got}"
        )
    cocotb.log.info(
        f"  {len(payloads)} blocks at a {SAFE_BLOCK_GAP}-clock gap, all verified"
    )

    cocotb.log.info("STEP 4: sustained streaming in IFFT mode at the same pacing")
    await bring_up(dut, inverse=True)
    nbf_in_i, nbf_out_i = formats(True)
    models = [build_model(True) for _ in seeds]
    payloads = [random_block(m, nbf_in_i, s) for m, s in zip(models, seeds)]
    wanted = [expected_serial(m, b, nbf_out_i) for m, b in zip(models, payloads)]

    received = await stream_many_blocks(dut, payloads, nbf_in_i, SAFE_BLOCK_GAP)
    for idx, (got, want) in enumerate(zip(received, wanted)):
        assert got == want, (
            f"sustained IFFT block {idx}: expected {want}, got {got}"
        )
    cocotb.log.info(f"  {len(payloads)} IFFT blocks at the same pacing, all verified")
    cocotb.log.info("test_bringup_13_block_pacing PASSED")
