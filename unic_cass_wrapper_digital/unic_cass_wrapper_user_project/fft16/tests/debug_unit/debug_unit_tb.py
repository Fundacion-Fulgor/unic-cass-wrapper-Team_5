import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
import random

CLK_SYS_NS = 20
CLK_SPI_NS = 100

ADDR_STATUS_FLAGS = 0x00
ADDR_ERROR_FLAGS  = 0x01
ADDR_CNT_INPUTS   = 0x02
ADDR_CNT_OUTPUTS  = 0x03
ADDR_LAST_OUT_RE  = 0x04
ADDR_LAST_OUT_IM  = 0x05
ADDR_MID_DATA_RE  = 0x06
ADDR_SYS_CONFIG   = 0x10


async def reset_dut(dut):
    dut.i_rstn.value        = 0
    dut.i_spi_addr.value     = 0
    dut.i_spi_wdata.value    = 0
    dut.i_spi_rw.value       = 1   # default READ
    dut.i_spi_ss_n.value     = 1
    dut.i_status_flags.value = 0
    dut.i_error_flags.value  = 0
    dut.i_cnt_inputs.value   = 0
    dut.i_cnt_outputs.value  = 0
    dut.i_last_out_re.value  = 0
    dut.i_last_out_im.value  = 0
    dut.i_mid_data_re.value  = 0
    for _ in range(4):
        await RisingEdge(dut.i_clk)
    dut.i_rstn.value = 1
    await RisingEdge(dut.i_clk)


async def trigger_snapshot(dut):
    """
    Pulls ss_n low asynchronously to freeze probe inputs via cdc_snapshot,
    then releases it. rw_rw stays 1 (READ) so no write is committed.
    """
    await Timer(CLK_SPI_NS, unit="ns")
    dut.i_spi_ss_n.value = 0
    for _ in range(5):
        await RisingEdge(dut.i_clk)
    dut.i_spi_ss_n.value = 1
    for _ in range(6):
        await RisingEdge(dut.i_clk)


async def spi_write(dut, addr, data):
    """
    Simulates a complete SPI write transaction using rw_bit (0=WRITE).
    rw_bit is stable from the 8th sclk cycle — here we set it before
    ss_n falls to replicate that the master has already decided to write.
    ss_n falls  -> snapshot_pulse (status frozen)
    data settles in SPI domain
    ss_n rises  -> commit_pulse captures addr/wdata/rw_snap
    commit_pulse_q -> sys_config written
    """
    dut.i_spi_rw.value    = 0   # WRITE
    dut.i_spi_addr.value  = addr
    dut.i_spi_wdata.value = data
    await Timer(CLK_SPI_NS, unit="ns")
    dut.i_spi_ss_n.value = 0
    for _ in range(5):
        await RisingEdge(dut.i_clk)
    await Timer(CLK_SPI_NS, unit="ns")
    dut.i_spi_ss_n.value = 1
    for _ in range(6):
        await RisingEdge(dut.i_clk)
    dut.i_spi_rw.value = 1   # back to READ


async def spi_read(dut, addr):
    """
    Reads spi_rdata combinationally via spi_addr directly.
    No transaction needed — frozen snapshot values remain stable.
    """
    dut.i_spi_addr.value = addr
    await RisingEdge(dut.i_clk)
    return int(dut.o_spi_rdata.value)


@cocotb.test()
async def test_sys_config_write(dut):
    """
    Writes different values to sys_config via full SPI write transactions.
    Uses spi_rw=0 (WRITE) stable before ss_n falls, mimicking real
    spi_slave_mode0 behavior where rw_bit is latched at the 8th sclk cycle.
    """
    cocotb.start_soon(Clock(dut.i_clk, CLK_SYS_NS, unit="ns").start())
    await reset_dut(dut)
    cocotb.log.info("--- test_sys_config_write ---")

    for val in [0b000, 0b001, 0b010, 0b011, 0b100, 0b101, 0b110, 0b111]:
        await spi_write(dut, ADDR_SYS_CONFIG, val)
        got = int(dut.o_sys_config.value)
        assert got == val, \
            f"sys_config mismatch: wrote {val:#05b}, got {got:#05b}"
        cocotb.log.info(f"  sys_config = {val:#05b}  OK")

    cocotb.log.info("test_sys_config_write PASSED.")


@cocotb.test()
async def test_sys_config_readback(dut):
    """
    Writes sys_config and reads it back via spi_rdata.
    """
    cocotb.start_soon(Clock(dut.i_clk, CLK_SYS_NS, unit="ns").start())
    await reset_dut(dut)
    cocotb.log.info("--- test_sys_config_readback ---")

    for val in [0b001, 0b011, 0b111]:
        await spi_write(dut, ADDR_SYS_CONFIG, val)
        got = await spi_read(dut, ADDR_SYS_CONFIG)
        assert got == val, \
            f"sys_config readback mismatch: expected {val:#05b}, got {got:#05b}"
        cocotb.log.info(f"  readback sys_config = {val:#05b}  OK")

    cocotb.log.info("test_sys_config_readback PASSED.")


@cocotb.test()
async def test_status_snapshot(dut):
    """
    Sets known values on all probe inputs, triggers a snapshot explicitly,
    then reads each register and verifies the frozen value.
    """
    cocotb.start_soon(Clock(dut.i_clk, CLK_SYS_NS, unit="ns").start())
    await reset_dut(dut)
    cocotb.log.info("--- test_status_snapshot ---")

    dut.i_status_flags.value = 0xAB
    dut.i_error_flags.value  = 0x01
    dut.i_cnt_inputs.value   = 0x42
    dut.i_cnt_outputs.value  = 0x10
    dut.i_last_out_re.value  = 0x7F
    dut.i_last_out_im.value  = 0x3C
    dut.i_mid_data_re.value  = 0x55

    for _ in range(3):
        await RisingEdge(dut.i_clk)

    await trigger_snapshot(dut)

    checks = [
        (ADDR_STATUS_FLAGS, 0xAB, "status_flags"),
        (ADDR_ERROR_FLAGS,  0x01, "error_flags"),
        (ADDR_CNT_INPUTS,   0x42, "cnt_inputs"),
        (ADDR_CNT_OUTPUTS,  0x10, "cnt_outputs"),
        (ADDR_LAST_OUT_RE,  0x7F, "last_out_re"),
        (ADDR_LAST_OUT_IM,  0x3C, "last_out_im"),
        (ADDR_MID_DATA_RE,  0x55, "mid_data_re"),
    ]

    for addr, expected, name in checks:
        got = await spi_read(dut, addr)
        assert got == expected, \
            f"{name} snapshot mismatch: expected {expected:#04x}, got {got:#04x}"
        cocotb.log.info(f"  {name} @ {addr:#04x} = {got:#04x}  OK")

    cocotb.log.info("test_status_snapshot PASSED.")


@cocotb.test()
async def test_cdc_snapshot_freeze(dut):
    """
    Verifies that changes to probe inputs after ss_n falls do not modify
    the frozen snapshot. The snapshot captures what was present at the
    falling edge of ss_n.
    """
    cocotb.start_soon(Clock(dut.i_clk, CLK_SYS_NS, unit="ns").start())
    await reset_dut(dut)
    cocotb.log.info("--- test_cdc_snapshot_freeze ---")

    dut.i_cnt_inputs.value  = 0x11
    dut.i_cnt_outputs.value = 0x22
    dut.i_last_out_re.value = 0x33
    dut.i_last_out_im.value = 0x44

    for _ in range(3):
        await RisingEdge(dut.i_clk)

    await Timer(CLK_SPI_NS, unit="ns")
    dut.i_spi_ss_n.value = 0
    for _ in range(5):
        await RisingEdge(dut.i_clk)

    # Change inputs while ss_n is still low — must not affect frozen snapshot
    dut.i_cnt_inputs.value  = 0xFF
    dut.i_cnt_outputs.value = 0xEE
    dut.i_last_out_re.value = 0xDD
    dut.i_last_out_im.value = 0xCC

    for _ in range(5):
        await RisingEdge(dut.i_clk)
    dut.i_spi_ss_n.value = 1
    for _ in range(6):
        await RisingEdge(dut.i_clk)

    checks = [
        (ADDR_CNT_INPUTS,  0x11, "cnt_inputs"),
        (ADDR_CNT_OUTPUTS, 0x22, "cnt_outputs"),
        (ADDR_LAST_OUT_RE, 0x33, "last_out_re"),
        (ADDR_LAST_OUT_IM, 0x44, "last_out_im"),
    ]

    for addr, expected, name in checks:
        got = await spi_read(dut, addr)
        assert got == expected, \
            f"{name} freeze failed: expected {expected:#04x}, got {got:#04x}"
        cocotb.log.info(f"  {name} frozen @ {expected:#04x}  OK")

    cocotb.log.info("test_cdc_snapshot_freeze PASSED.")


@cocotb.test()
async def test_cdc_snapshot_update(dut):
    """
    Two consecutive snapshots with different values. Each must capture
    what was present at its respective ss_n falling edge.
    """
    cocotb.start_soon(Clock(dut.i_clk, CLK_SYS_NS, unit="ns").start())
    await reset_dut(dut)
    cocotb.log.info("--- test_cdc_snapshot_update ---")

    dut.i_cnt_inputs.value  = 0xAA
    dut.i_last_out_re.value = 0xBB
    for _ in range(3):
        await RisingEdge(dut.i_clk)
    await trigger_snapshot(dut)

    got_inputs = await spi_read(dut, ADDR_CNT_INPUTS)
    got_re     = await spi_read(dut, ADDR_LAST_OUT_RE)
    assert got_inputs == 0xAA, \
        f"First snapshot cnt_inputs: expected 0xAA, got {got_inputs:#04x}"
    assert got_re == 0xBB, \
        f"First snapshot last_out_re: expected 0xBB, got {got_re:#04x}"
    cocotb.log.info(
        f"  First snapshot: cnt_inputs={got_inputs:#04x}  last_out_re={got_re:#04x}  OK"
    )

    dut.i_cnt_inputs.value  = 0x12
    dut.i_last_out_re.value = 0x34
    for _ in range(3):
        await RisingEdge(dut.i_clk)
    await trigger_snapshot(dut)

    got_inputs = await spi_read(dut, ADDR_CNT_INPUTS)
    got_re     = await spi_read(dut, ADDR_LAST_OUT_RE)
    assert got_inputs == 0x12, \
        f"Second snapshot cnt_inputs: expected 0x12, got {got_inputs:#04x}"
    assert got_re == 0x34, \
        f"Second snapshot last_out_re: expected 0x34, got {got_re:#04x}"
    cocotb.log.info(
        f"  Second snapshot: cnt_inputs={got_inputs:#04x}  last_out_re={got_re:#04x}  OK"
    )

    cocotb.log.info("test_cdc_snapshot_update PASSED.")


@cocotb.test()
async def test_default_address(dut):
    """
    Reads from unmapped addresses and verifies spi_rdata returns 0x00.
    """
    cocotb.start_soon(Clock(dut.i_clk, CLK_SYS_NS, unit="ns").start())
    await reset_dut(dut)
    cocotb.log.info("--- test_default_address ---")

    for addr in [0x07, 0x0F, 0x11, 0x7F]:
        got = await spi_read(dut, addr)
        assert got == 0x00, \
            f"Unmapped address {addr:#04x}: expected 0x00, got {got:#04x}"
        cocotb.log.info(f"  addr {addr:#04x} -> {got:#04x}  OK")

    cocotb.log.info("test_default_address PASSED.")


@cocotb.test()
async def test_random_snapshot(dut):
    """
    Random probe values, random settle time, explicit snapshot trigger,
    then inputs change and frozen values are verified.
    """
    cocotb.start_soon(Clock(dut.i_clk, CLK_SYS_NS, unit="ns").start())
    await reset_dut(dut)
    cocotb.log.info("--- test_random_snapshot ---")

    random.seed(7)

    for iteration in range(8):
        vals = {
            "status_flags": random.randint(0, 0xFF),
            "error_flags":  random.randint(0, 0xFF),
            "cnt_inputs":   random.randint(0, 0xFF),
            "cnt_outputs":  random.randint(0, 0xFF),
            "last_out_re":  random.randint(0, 0xFF),
            "last_out_im":  random.randint(0, 0xFF),
            "mid_data_re":  random.randint(0, 0xFF),
        }

        for name, val in vals.items():
            getattr(dut, "i_" + name).value = val

        for _ in range(random.randint(2, 8)):
            await RisingEdge(dut.i_clk)

        await trigger_snapshot(dut)

        # Change all inputs after snapshot
        for name in vals:
            getattr(dut, "i_" + name).value = random.randint(0, 0xFF)

        for _ in range(3):
            await RisingEdge(dut.i_clk)

        checks = [
            (ADDR_STATUS_FLAGS, vals["status_flags"], "status_flags"),
            (ADDR_ERROR_FLAGS,  vals["error_flags"],  "error_flags"),
            (ADDR_CNT_INPUTS,   vals["cnt_inputs"],   "cnt_inputs"),
            (ADDR_CNT_OUTPUTS,  vals["cnt_outputs"],  "cnt_outputs"),
            (ADDR_LAST_OUT_RE,  vals["last_out_re"],  "last_out_re"),
            (ADDR_LAST_OUT_IM,  vals["last_out_im"],  "last_out_im"),
            (ADDR_MID_DATA_RE,  vals["mid_data_re"],  "mid_data_re"),
        ]

        for addr, expected, name in checks:
            got = await spi_read(dut, addr)
            assert got == expected, \
                f"Iter {iteration} - {name}: expected {expected:#04x}, got {got:#04x}"

        cocotb.log.info(f"  Iteration {iteration} PASSED")

    cocotb.log.info("test_random_snapshot PASSED.")

PROBE_SIGNALS = [
    ("status_flags", ADDR_STATUS_FLAGS),
    ("error_flags", ADDR_ERROR_FLAGS),
    ("cnt_inputs", ADDR_CNT_INPUTS),
    ("cnt_outputs", ADDR_CNT_OUTPUTS),
    ("last_out_re", ADDR_LAST_OUT_RE),
    ("last_out_im", ADDR_LAST_OUT_IM),
    ("mid_data_re", ADDR_MID_DATA_RE),
]

MAPPED_ADDRESSES = [addr for _, addr in PROBE_SIGNALS] + [ADDR_SYS_CONFIG]


async def set_probes_and_snapshot(dut, value_map):
    for name, value in value_map.items():
        getattr(dut, "i_" + name).value = value
    for _ in range(3):
        await RisingEdge(dut.i_clk)
    await trigger_snapshot(dut)


@cocotb.test()
async def test_reset_state(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_SYS_NS, unit="ns").start())
    await reset_dut(dut)

    assert int(dut.o_sys_config.value) == 0, "sys_config must reset to 0b000"
    for name, addr in PROBE_SIGNALS:
        got = await spi_read(dut, addr)
        assert got == 0, f"{name} snapshot must reset to 0, got {got:#04x}"
    cocotb.log.info("All snapshot registers and sys_config reset to zero OK")


@cocotb.test()
async def test_exhaustive_probe_values(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_SYS_NS, unit="ns").start())
    await reset_dut(dut)

    for value in range(0, 256, 5):
        await set_probes_and_snapshot(dut, {name: value for name, _ in PROBE_SIGNALS})
        for name, addr in PROBE_SIGNALS:
            got = await spi_read(dut, addr)
            assert got == value, (
                f"{name}: expected {value:#04x}, got {got:#04x}"
            )
    cocotb.log.info("Swept probe values across the full 8-bit range OK")


@cocotb.test()
async def test_each_probe_is_independent(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_SYS_NS, unit="ns").start())
    await reset_dut(dut)

    for target, target_addr in PROBE_SIGNALS:
        values = {name: 0x00 for name, _ in PROBE_SIGNALS}
        values[target] = 0xA5
        await set_probes_and_snapshot(dut, values)
        for name, addr in PROBE_SIGNALS:
            got = await spi_read(dut, addr)
            expected = 0xA5 if name == target else 0x00
            assert got == expected, (
                f"reading {name} while only {target} was set: "
                f"expected {expected:#04x}, got {got:#04x}"
            )
        cocotb.log.info(f"  {target} @ {target_addr:#04x} is independent OK")
    cocotb.log.info("Each probe maps to its own address OK")


@cocotb.test()
async def test_all_unmapped_addresses_read_zero(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_SYS_NS, unit="ns").start())
    await reset_dut(dut)

    await set_probes_and_snapshot(dut, {name: 0xFF for name, _ in PROBE_SIGNALS})
    await spi_write(dut, ADDR_SYS_CONFIG, 0b111)

    for addr in range(128):
        if addr in MAPPED_ADDRESSES:
            continue
        got = await spi_read(dut, addr)
        assert got == 0x00, (
            f"unmapped address {addr:#04x} must read 0x00, got {got:#04x}"
        )
    cocotb.log.info("All 120 unmapped addresses read back zero OK")


@cocotb.test()
async def test_write_to_read_only_address_ignored(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_SYS_NS, unit="ns").start())
    await reset_dut(dut)

    await spi_write(dut, ADDR_SYS_CONFIG, 0b101)
    assert int(dut.o_sys_config.value) == 0b101

    for _, addr in PROBE_SIGNALS:
        await spi_write(dut, addr, 0b010)
        assert int(dut.o_sys_config.value) == 0b101, (
            f"a write to {addr:#04x} must not change sys_config"
        )
    cocotb.log.info("Writes to probe addresses never touch sys_config OK")


@cocotb.test()
async def test_read_transaction_does_not_write(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_SYS_NS, unit="ns").start())
    await reset_dut(dut)

    await spi_write(dut, ADDR_SYS_CONFIG, 0b011)
    assert int(dut.o_sys_config.value) == 0b011

    dut.i_spi_rw.value = 1
    dut.i_spi_addr.value = ADDR_SYS_CONFIG
    dut.i_spi_wdata.value = 0b100
    for _ in range(5):
        await trigger_snapshot(dut)
        assert int(dut.o_sys_config.value) == 0b011, (
            "a READ transaction must never commit write data"
        )
    cocotb.log.info("Read transactions do not modify sys_config OK")


@cocotb.test()
async def test_sys_config_uses_low_three_bits(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_SYS_NS, unit="ns").start())
    await reset_dut(dut)

    for value in range(256):
        await spi_write(dut, ADDR_SYS_CONFIG, value)
        got = int(dut.o_sys_config.value)
        assert got == (value & 0b111), (
            f"wrote {value:#04x}: expected sys_config {value & 0b111:#05b}, "
            f"got {got:#05b}"
        )
    cocotb.log.info("All 256 write values map to the low three sys_config bits OK")


@cocotb.test()
async def test_sys_config_readback_upper_bits_zero(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_SYS_NS, unit="ns").start())
    await reset_dut(dut)

    for value in range(8):
        await spi_write(dut, ADDR_SYS_CONFIG, value)
        got = await spi_read(dut, ADDR_SYS_CONFIG)
        assert got == value, (
            f"sys_config readback: expected {value:#04x}, got {got:#04x}"
        )
    cocotb.log.info("sys_config reads back with zeroed upper bits OK")


@cocotb.test()
async def test_snapshot_not_triggered_without_ss_n(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_SYS_NS, unit="ns").start())
    await reset_dut(dut)

    await set_probes_and_snapshot(dut, {name: 0x3C for name, _ in PROBE_SIGNALS})
    for name, _ in PROBE_SIGNALS:
        getattr(dut, "i_" + name).value = 0xC3
    for _ in range(40):
        await RisingEdge(dut.i_clk)
    for name, addr in PROBE_SIGNALS:
        got = await spi_read(dut, addr)
        assert got == 0x3C, (
            f"{name} changed without a new ss_n falling edge: got {got:#04x}"
        )
    cocotb.log.info("Probes stay frozen until the next ss_n falling edge OK")


@cocotb.test()
async def test_repeated_config_writes(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_SYS_NS, unit="ns").start())
    await reset_dut(dut)

    random.seed(141)
    for _ in range(60):
        value = random.randint(0, 7)
        await spi_write(dut, ADDR_SYS_CONFIG, value)
        assert int(dut.o_sys_config.value) == value, (
            f"sys_config write failed for {value:#05b}"
        )
        got = await spi_read(dut, ADDR_SYS_CONFIG)
        assert got == value, f"sys_config readback failed for {value:#05b}"
    cocotb.log.info("60 random back-to-back config writes OK")


@cocotb.test()
async def test_reset_clears_config_and_snapshots(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_SYS_NS, unit="ns").start())
    await reset_dut(dut)

    await spi_write(dut, ADDR_SYS_CONFIG, 0b111)
    await set_probes_and_snapshot(dut, {name: 0xFF for name, _ in PROBE_SIGNALS})
    assert int(dut.o_sys_config.value) == 0b111

    await reset_dut(dut)
    assert int(dut.o_sys_config.value) == 0, "reset must clear sys_config"
    for name, addr in PROBE_SIGNALS:
        got = await spi_read(dut, addr)
        assert got == 0, f"reset must clear the {name} snapshot, got {got:#04x}"
    cocotb.log.info("Reset clears both config and all snapshots OK")
