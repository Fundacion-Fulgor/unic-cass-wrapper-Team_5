import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
import random

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CLK_SYS_NS  = 20   # 50 MHz system clock
SPI_HALF_NS = 50   # 10 MHz SPI clock — half period

ADDR_STATUS_FLAGS = 0x00
ADDR_ERROR_FLAGS  = 0x01
ADDR_CNT_INPUTS   = 0x02
ADDR_CNT_OUTPUTS  = 0x03
ADDR_LAST_OUT_RE  = 0x04
ADDR_LAST_OUT_IM  = 0x05
ADDR_MID_DATA_RE  = 0x06
ADDR_SYS_CONFIG   = 0x10

RW_WRITE = 0
RW_READ  = 1

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def reset_dut(dut):
    dut.i_rstn.value        = 0
    dut.i_ss_n.value         = 1
    dut.i_sclk.value         = 0
    dut.i_mosi.value         = 0
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


async def spi_master_transfer(dut, rw, addr, wdata=0x00):
    """
    Executes a full 16-bit SPI transaction (Mode 0: CPOL=0, CPHA=0).
    Frame: [RW(1)][ADDR(7)][DATA(8)] sent MSB first.
    RW=1: READ, RW=0: WRITE.

    MISO timing:
      The spi_slave_mode0 decodes the header at bit_cnt==7 (8th posedge).
      On the following negedge it loads tx_shift with data_in (spi_rdata).
      MISO = tx_shift[15] combinationally, so it is valid after that negedge.
      The master samples MISO after each negedge for i in [7..14], giving
      data_in[7:0] = the frozen register value for READ transactions.

    For WRITE transactions the returned value is meaningless.
    After ss_n rises, waits enough system clock cycles for commit_pulse_q
    to propagate and write sys_config if applicable.
    """
    frame = ((rw & 1) << 15) | ((addr & 0x7F) << 8) | (wdata & 0xFF)

    # ss_n falls — triggers cdc_snapshot (falling edge detector in system domain)
    dut.i_ss_n.value  = 0
    dut.i_sclk.value  = 0
    dut.i_mosi.value  = 0
    await Timer(SPI_HALF_NS, unit="ns")

    miso_byte = 0

    for i in range(16):
        # Set MOSI before rising edge (MSB first)
        dut.i_mosi.value = (frame >> (15 - i)) & 1
        await Timer(SPI_HALF_NS, unit="ns")

        # Rising edge — slave samples MOSI
        dut.i_sclk.value = 1
        await Timer(SPI_HALF_NS, unit="ns")

        # Falling edge — slave updates tx_shift / MISO
        dut.i_sclk.value = 0
        await Timer(SPI_HALF_NS, unit="ns")

        # Sample MISO after negedge during data byte:
        #   i=7:  negedge loads tx_shift  -> MISO = data_in[7]
        #   i=8:  first shift             -> MISO = data_in[6]
        #   ...
        #   i=14: seventh shift           -> MISO = data_in[0]
        if 7 <= i <= 14:
            miso_byte = (miso_byte << 1) | int(dut.o_miso.value)

    # ss_n rises — triggers commit_pulse in debug_unit
    dut.i_ss_n.value = 1
    await Timer(SPI_HALF_NS, unit="ns")

    # Wait for commit_pulse and commit_pulse_q to propagate in system domain
    for _ in range(8):
        await RisingEdge(dut.i_clk)

    return miso_byte


async def spi_write(dut, addr, data):
    await spi_master_transfer(dut, RW_WRITE, addr, data)


async def spi_read(dut, addr):
    return await spi_master_transfer(dut, RW_READ, addr)


# ---------------------------------------------------------------------------
# Test 1: Write sys_config via real SPI and verify output port
# ---------------------------------------------------------------------------

@cocotb.test()
async def test_spi_write_sys_config(dut):
    """
    Writes different values to sys_config (0x10) using real SPI frames.
    Verifies the sys_config output port after each write.
    Exercises the full path: MOSI bits -> spi_slave_mode0 -> rw_bit/addr_out/data_out
    -> commit_pulse in debug_unit -> sys_config register.
    """
    cocotb.start_soon(Clock(dut.i_clk, CLK_SYS_NS, unit="ns").start())
    await reset_dut(dut)
    cocotb.log.info("--- test_spi_write_sys_config ---")

    test_vectors = [0b000, 0b001, 0b010, 0b011, 0b100, 0b101, 0b110, 0b111]

    for val in test_vectors:
        await spi_write(dut, ADDR_SYS_CONFIG, val)
        got = int(dut.o_sys_config.value)
        assert got == val, \
            f"sys_config mismatch: wrote {val:#05b}, got {got:#05b}"
        cocotb.log.info(f"  sys_config = {val:#05b}  OK")

    cocotb.log.info("test_spi_write_sys_config PASSED.")


# ---------------------------------------------------------------------------
# Test 2: Read status register via MISO
# ---------------------------------------------------------------------------

@cocotb.test()
async def test_spi_read_status_register(dut):
    """
    Sets known values on all probe inputs, performs a real SPI READ for each
    register address, and verifies the value received on MISO.
    Exercises the full path: cdc_snapshot freeze -> spi_rdata -> tx_shift -> MISO.
    """
    cocotb.start_soon(Clock(dut.i_clk, CLK_SYS_NS, unit="ns").start())
    await reset_dut(dut)
    cocotb.log.info("--- test_spi_read_status_register ---")

    dut.i_status_flags.value = 0xAB
    dut.i_error_flags.value  = 0x01
    dut.i_cnt_inputs.value   = 0x42
    dut.i_cnt_outputs.value  = 0x10
    dut.i_last_out_re.value  = 0x7F
    dut.i_last_out_im.value  = 0x3C
    dut.i_mid_data_re.value  = 0x55

    for _ in range(3):
        await RisingEdge(dut.i_clk)

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
            f"{name} MISO mismatch: expected {expected:#04x}, got {got:#04x}"
        cocotb.log.info(f"  {name} @ {addr:#04x} = {got:#04x}  OK")

    cocotb.log.info("test_spi_read_status_register PASSED.")


# ---------------------------------------------------------------------------
# Test 3: Write sys_config then read it back via MISO
# ---------------------------------------------------------------------------

@cocotb.test()
async def test_spi_read_sys_config(dut):
    """
    Writes sys_config via SPI WRITE, then reads it back via SPI READ.
    Verifies that the read mux correctly returns sys_config at address 0x10.
    """
    cocotb.start_soon(Clock(dut.i_clk, CLK_SYS_NS, unit="ns").start())
    await reset_dut(dut)
    cocotb.log.info("--- test_spi_read_sys_config ---")

    for val in [0b001, 0b011, 0b101, 0b111]:
        await spi_write(dut, ADDR_SYS_CONFIG, val)
        got = await spi_read(dut, ADDR_SYS_CONFIG)
        assert got == val, \
            f"sys_config readback mismatch: expected {val:#05b}, got {got:#05b}"
        cocotb.log.info(f"  readback sys_config = {val:#05b}  OK")

    cocotb.log.info("test_spi_read_sys_config PASSED.")


# ---------------------------------------------------------------------------
# Test 4: CDC — probe inputs changed mid-transaction do not corrupt snapshot
# ---------------------------------------------------------------------------

@cocotb.test()
async def test_cdc_snapshot_timing(dut):
    """
    Verifies the CDC snapshot timing with real SPI clocking.
    Protocol:
      1. Set probe inputs to known values A.
      2. Pull ss_n low — cdc_snapshot captures A.
      3. Wait for snapshot to propagate through double-flop synchronizer.
      4. Change probe inputs to B while ss_n is still low.
      5. Complete the SPI READ transaction.
      6. Verify MISO returns A (frozen), not B (live).
    """
    cocotb.start_soon(Clock(dut.i_clk, CLK_SYS_NS, unit="ns").start())
    await reset_dut(dut)
    cocotb.log.info("--- test_cdc_snapshot_timing ---")

    # Step 1: set initial probe values (to be captured in snapshot)
    dut.i_cnt_inputs.value  = 0x11
    dut.i_cnt_outputs.value = 0x22
    dut.i_last_out_re.value = 0x33

    for _ in range(3):
        await RisingEdge(dut.i_clk)

    # Step 2: ss_n falls — snapshot is triggered asynchronously
    dut.i_ss_n.value  = 0
    dut.i_sclk.value  = 0
    dut.i_mosi.value  = 0
    await Timer(SPI_HALF_NS, unit="ns")

    # Step 3: wait for snapshot to propagate through system clock synchronizer
    # (minimum 3 system cycles, using 5 for margin)
    for _ in range(5):
        await RisingEdge(dut.i_clk)

    # Step 4: change probe inputs while ss_n is still low
    dut.i_cnt_inputs.value  = 0xFF
    dut.i_cnt_outputs.value = 0xEE
    dut.i_last_out_re.value = 0xDD

    for _ in range(3):
        await RisingEdge(dut.i_clk)

    # Step 5: clock out READ frame for ADDR_CNT_INPUTS
    frame    = (RW_READ << 15) | (ADDR_CNT_INPUTS << 8) | 0x00
    miso_cnt = 0

    for i in range(16):
        dut.i_mosi.value = (frame >> (15 - i)) & 1
        await Timer(SPI_HALF_NS, unit="ns")
        dut.i_sclk.value = 1
        await Timer(SPI_HALF_NS, unit="ns")
        dut.i_sclk.value = 0
        await Timer(SPI_HALF_NS, unit="ns")
        if 7 <= i <= 14:
            miso_cnt = (miso_cnt << 1) | int(dut.o_miso.value)

    dut.i_ss_n.value = 1
    await Timer(SPI_HALF_NS, unit="ns")
    for _ in range(8):
        await RisingEdge(dut.i_clk)

    # Step 6: MISO must return 0x11 (frozen), not 0xFF (live)
    assert miso_cnt == 0x11, \
        f"CDC freeze failed on cnt_inputs: expected 0x11, got {miso_cnt:#04x}"
    cocotb.log.info(f"  cnt_inputs frozen correctly: {miso_cnt:#04x}  OK")

    # Verify cnt_outputs with a new READ (new snapshot will capture 0xEE now)
    got_outputs = await spi_read(dut, ADDR_CNT_OUTPUTS)
    assert got_outputs == 0xEE, \
        f"After freeze: cnt_outputs expected 0xEE (new snap), got {got_outputs:#04x}"
    cocotb.log.info(f"  cnt_outputs after new snapshot: {got_outputs:#04x}  OK")

    cocotb.log.info("test_cdc_snapshot_timing PASSED.")


# ---------------------------------------------------------------------------
# Test 5: Random writes and reads with random probe values
# ---------------------------------------------------------------------------

@cocotb.test()
async def test_random_rw(dut):
    """
    Random sequence of SPI reads and writes.
    For each iteration:
      - Sets random probe values.
      - Reads each status register via SPI and verifies MISO against
        the values present at the time ss_n fell (frozen snapshot).
      - Writes a random value to sys_config and verifies the output port.
    """
    cocotb.start_soon(Clock(dut.i_clk, CLK_SYS_NS, unit="ns").start())
    await reset_dut(dut)
    cocotb.log.info("--- test_random_rw ---")

    random.seed(42)

    for iteration in range(6):
        probe_vals = {
            "status_flags": random.randint(0, 0xFF),
            "error_flags":  random.randint(0, 0xFF),
            "cnt_inputs":   random.randint(0, 0xFF),
            "cnt_outputs":  random.randint(0, 0xFF),
            "last_out_re":  random.randint(0, 0xFF),
            "last_out_im":  random.randint(0, 0xFF),
            "mid_data_re":  random.randint(0, 0xFF),
        }

        for name, val in probe_vals.items():
            getattr(dut, "i_" + name).value = val

        # Let values settle in system domain
        for _ in range(random.randint(2, 6)):
            await RisingEdge(dut.i_clk)

        # Read each status register — each SPI transaction snapshots current values
        # We read one by one so each transaction freezes the current probe state
        checks = [
            (ADDR_STATUS_FLAGS, probe_vals["status_flags"], "status_flags"),
            (ADDR_ERROR_FLAGS,  probe_vals["error_flags"],  "error_flags"),
            (ADDR_CNT_INPUTS,   probe_vals["cnt_inputs"],   "cnt_inputs"),
            (ADDR_CNT_OUTPUTS,  probe_vals["cnt_outputs"],  "cnt_outputs"),
            (ADDR_LAST_OUT_RE,  probe_vals["last_out_re"],  "last_out_re"),
            (ADDR_LAST_OUT_IM,  probe_vals["last_out_im"],  "last_out_im"),
            (ADDR_MID_DATA_RE,  probe_vals["mid_data_re"],  "mid_data_re"),
        ]

        for addr, expected, name in checks:
            got = await spi_read(dut, addr)
            assert got == expected, \
                f"Iter {iteration} - {name}: expected {expected:#04x}, got {got:#04x}"
            cocotb.log.info(f"  [{iteration}] {name} = {got:#04x}  OK")

        # Write random value to sys_config and verify
        cfg_val = random.randint(0, 7)
        await spi_write(dut, ADDR_SYS_CONFIG, cfg_val)
        got_cfg = int(dut.o_sys_config.value)
        assert got_cfg == cfg_val, \
            f"Iter {iteration} - sys_config: expected {cfg_val:#05b}, got {got_cfg:#05b}"
        cocotb.log.info(f"  [{iteration}] sys_config = {got_cfg:#05b}  OK")

    cocotb.log.info("test_random_rw PASSED.")

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


def set_probes(dut, value_map):
    for name, value in value_map.items():
        getattr(dut, "i_" + name).value = value


async def settle(dut, cycles=4):
    for _ in range(cycles):
        await RisingEdge(dut.i_clk)


@cocotb.test()
async def test_reset_state(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_SYS_NS, unit="ns").start())
    await reset_dut(dut)

    assert int(dut.o_sys_config.value) == 0, "sys_config must reset to 0b000"
    assert int(dut.o_miso.value) == 0, "miso must idle low while deselected"
    for name, addr in PROBE_SIGNALS:
        got = await spi_read(dut, addr)
        assert got == 0, f"{name} must read 0 after reset, got {got:#04x}"
    cocotb.log.info("Reset state of the whole debug system OK")


@cocotb.test()
async def test_read_every_probe_register(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_SYS_NS, unit="ns").start())
    await reset_dut(dut)

    values = {
        "status_flags": 0x0F,
        "error_flags": 0x01,
        "cnt_inputs": 0x10,
        "cnt_outputs": 0x10,
        "last_out_re": 0x7F,
        "last_out_im": 0x80,
        "mid_data_re": 0x5A,
    }
    set_probes(dut, values)
    await settle(dut)

    for name, addr in PROBE_SIGNALS:
        got = await spi_read(dut, addr)
        assert got == values[name], (
            f"{name} @ {addr:#04x}: expected {values[name]:#04x}, got {got:#04x}"
        )
        cocotb.log.info(f"  {name} @ {addr:#04x} = {got:#04x} OK")
    cocotb.log.info("Every probe register is readable over SPI OK")


@cocotb.test()
async def test_exhaustive_read_values(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_SYS_NS, unit="ns").start())
    await reset_dut(dut)

    for value in range(0, 256, 3):
        set_probes(dut, {"cnt_inputs": value, "last_out_re": 255 - value})
        await settle(dut)
        got_a = await spi_read(dut, ADDR_CNT_INPUTS)
        got_b = await spi_read(dut, ADDR_LAST_OUT_RE)
        assert got_a == value, f"cnt_inputs: expected {value:#04x}, got {got_a:#04x}"
        assert got_b == 255 - value, (
            f"last_out_re: expected {255 - value:#04x}, got {got_b:#04x}"
        )
    cocotb.log.info("Swept read values across the 8-bit range OK")


@cocotb.test()
async def test_all_sys_config_values(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_SYS_NS, unit="ns").start())
    await reset_dut(dut)

    for value in range(256):
        await spi_write(dut, ADDR_SYS_CONFIG, value)
        got = int(dut.o_sys_config.value)
        assert got == (value & 0b111), (
            f"wrote {value:#04x}: expected {value & 0b111:#05b}, got {got:#05b}"
        )
    cocotb.log.info("All 256 write values drive the three sys_config bits OK")


@cocotb.test()
async def test_unmapped_addresses_read_zero(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_SYS_NS, unit="ns").start())
    await reset_dut(dut)

    set_probes(dut, {name: 0xFF for name, _ in PROBE_SIGNALS})
    await settle(dut)
    await spi_write(dut, ADDR_SYS_CONFIG, 0b111)

    for addr in [0x07, 0x08, 0x0F, 0x11, 0x20, 0x3F, 0x40, 0x55, 0x7E, 0x7F]:
        got = await spi_read(dut, addr)
        assert got == 0x00, (
            f"unmapped address {addr:#04x} must read 0x00, got {got:#04x}"
        )
    cocotb.log.info("Unmapped addresses read back zero over SPI OK")


@cocotb.test()
async def test_write_then_read_back(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_SYS_NS, unit="ns").start())
    await reset_dut(dut)

    for value in range(8):
        await spi_write(dut, ADDR_SYS_CONFIG, value)
        got = await spi_read(dut, ADDR_SYS_CONFIG)
        assert got == value, (
            f"sys_config read back {got:#05b} after writing {value:#05b}"
        )
        assert int(dut.o_sys_config.value) == value
    cocotb.log.info("Write followed by read returns the same sys_config OK")


@cocotb.test()
async def test_write_to_probe_address_does_not_change_config(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_SYS_NS, unit="ns").start())
    await reset_dut(dut)

    await spi_write(dut, ADDR_SYS_CONFIG, 0b101)
    for _, addr in PROBE_SIGNALS:
        await spi_write(dut, addr, 0b010)
        assert int(dut.o_sys_config.value) == 0b101, (
            f"a write to {addr:#04x} changed sys_config"
        )
    cocotb.log.info("Writes to probe addresses leave sys_config untouched OK")


@cocotb.test()
async def test_snapshot_frozen_during_transaction(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_SYS_NS, unit="ns").start())
    await reset_dut(dut)

    set_probes(dut, {"cnt_outputs": 0x42})
    await settle(dut)

    frame = (RW_READ << 15) | (ADDR_CNT_OUTPUTS << 8)
    dut.i_ss_n.value = 0
    dut.i_sclk.value = 0
    dut.i_mosi.value = 0
    await Timer(SPI_HALF_NS, unit="ns")
    miso_byte = 0
    for i in range(16):
        dut.i_mosi.value = (frame >> (15 - i)) & 1
        await Timer(SPI_HALF_NS, unit="ns")
        dut.i_sclk.value = 1
        await Timer(SPI_HALF_NS, unit="ns")
        dut.i_sclk.value = 0
        await Timer(SPI_HALF_NS, unit="ns")
        if i == 3:
            dut.i_cnt_outputs.value = 0xFF
        if 7 <= i <= 14:
            miso_byte = (miso_byte << 1) | int(dut.o_miso.value)
    dut.i_ss_n.value = 1
    await Timer(SPI_HALF_NS, unit="ns")
    await settle(dut, 8)

    assert miso_byte == 0x42, (
        f"the snapshot taken at ss_n fall must be returned, got {miso_byte:#04x}"
    )
    cocotb.log.info("Probe changes during a transaction do not corrupt the read OK")


@cocotb.test()
async def test_consecutive_reads_of_same_address(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_SYS_NS, unit="ns").start())
    await reset_dut(dut)

    random.seed(151)
    for _ in range(30):
        value = random.randint(0, 255)
        set_probes(dut, {"mid_data_re": value})
        await settle(dut)
        for _ in range(3):
            got = await spi_read(dut, ADDR_MID_DATA_RE)
            assert got == value, (
                f"repeated read: expected {value:#04x}, got {got:#04x}"
            )
    cocotb.log.info("Repeated reads of the same address are stable OK")


@cocotb.test()
async def test_interleaved_reads_and_writes(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_SYS_NS, unit="ns").start())
    await reset_dut(dut)

    random.seed(152)
    config = 0
    for _ in range(60):
        if random.random() < 0.5:
            config = random.randint(0, 7)
            await spi_write(dut, ADDR_SYS_CONFIG, config)
            assert int(dut.o_sys_config.value) == config
        else:
            value = random.randint(0, 255)
            set_probes(dut, {"cnt_inputs": value})
            await settle(dut)
            got = await spi_read(dut, ADDR_CNT_INPUTS)
            assert got == value, (
                f"interleaved read: expected {value:#04x}, got {got:#04x}"
            )
            assert int(dut.o_sys_config.value) == config, (
                "a read must not disturb the configuration"
            )
    cocotb.log.info("60 interleaved read and write transactions OK")


@cocotb.test()
async def test_reset_clears_everything(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_SYS_NS, unit="ns").start())
    await reset_dut(dut)

    set_probes(dut, {name: 0xFF for name, _ in PROBE_SIGNALS})
    await settle(dut)
    await spi_write(dut, ADDR_SYS_CONFIG, 0b111)
    await spi_read(dut, ADDR_STATUS_FLAGS)
    assert int(dut.o_sys_config.value) == 0b111

    set_probes(dut, {name: 0x00 for name, _ in PROBE_SIGNALS})
    await reset_dut(dut)
    assert int(dut.o_sys_config.value) == 0, "reset must clear sys_config"
    for name, addr in PROBE_SIGNALS:
        got = await spi_read(dut, addr)
        assert got == 0, f"reset must clear the {name} snapshot, got {got:#04x}"
    cocotb.log.info("Reset clears configuration and snapshots OK")


@cocotb.test()
async def test_miso_low_outside_data_phase(dut):
    cocotb.start_soon(Clock(dut.i_clk, CLK_SYS_NS, unit="ns").start())
    await reset_dut(dut)

    set_probes(dut, {"last_out_im": 0xFF})
    await settle(dut)

    frame = (RW_READ << 15) | (ADDR_LAST_OUT_IM << 8)
    dut.i_ss_n.value = 0
    dut.i_sclk.value = 0
    dut.i_mosi.value = 0
    await Timer(SPI_HALF_NS, unit="ns")
    for i in range(16):
        dut.i_mosi.value = (frame >> (15 - i)) & 1
        await Timer(SPI_HALF_NS, unit="ns")
        dut.i_sclk.value = 1
        await Timer(SPI_HALF_NS, unit="ns")
        dut.i_sclk.value = 0
        await Timer(SPI_HALF_NS, unit="ns")
        if i < 7:
            assert int(dut.o_miso.value) == 0, (
                f"miso must stay low during the header, bit {i} was high"
            )
    dut.i_ss_n.value = 1
    await Timer(SPI_HALF_NS, unit="ns")
    await settle(dut, 8)
    assert int(dut.o_miso.value) == 0, "miso must return low after deselect"
    cocotb.log.info("miso stays low outside the data phase OK")
