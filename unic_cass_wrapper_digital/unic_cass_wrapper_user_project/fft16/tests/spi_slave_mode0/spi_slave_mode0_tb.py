import random

import cocotb
from cocotb.triggers import Timer

HALF_NS = 50
FRAME_BITS = 16
ADDR_BITS = 7
DATA_BITS = 8
HDR_LAST_BIT = 7
MISO_FIRST_BIT = 8

RW_WRITE = 0
RW_READ = 1


def frame_of(rw, addr, data):
    return ((rw & 1) << 15) | ((addr & 0x7F) << 8) | (data & 0xFF)


async def reset_dut(dut):
    dut.i_rstn.value = 0
    dut.i_ss_n.value = 1
    dut.i_sclk.value = 0
    dut.i_mosi.value = 0
    dut.i_data.value = 0
    await Timer(HALF_NS * 4, unit="ns")
    dut.i_rstn.value = 1
    await Timer(HALF_NS * 2, unit="ns")


async def select(dut):
    dut.i_sclk.value = 0
    dut.i_mosi.value = 0
    dut.i_ss_n.value = 0
    await Timer(HALF_NS, unit="ns")


async def deselect(dut):
    dut.i_ss_n.value = 1
    await Timer(HALF_NS * 2, unit="ns")


async def shift_frame(dut, frame):
    miso_bits = []
    for i in range(FRAME_BITS):
        dut.i_mosi.value = (frame >> (FRAME_BITS - 1 - i)) & 1
        await Timer(HALF_NS, unit="ns")
        dut.i_sclk.value = 1
        await Timer(HALF_NS, unit="ns")
        miso_bits.append(int(dut.o_miso.value))
        dut.i_sclk.value = 0
        await Timer(HALF_NS, unit="ns")
    return miso_bits


def miso_byte(miso_bits):
    value = 0
    for bit in miso_bits[MISO_FIRST_BIT : MISO_FIRST_BIT + DATA_BITS]:
        value = (value << 1) | bit
    return value


async def transfer(dut, rw, addr, data=0x00, read_value=0x00):
    dut.i_data.value = read_value & 0xFF
    await select(dut)
    bits = await shift_frame(dut, frame_of(rw, addr, data))
    await deselect(dut)
    return miso_byte(bits)


@cocotb.test()
async def test_reset_state(dut):
    await reset_dut(dut)
    assert int(dut.o_addr.value) == 0, "addr_out must reset to 0"
    assert int(dut.o_data.value) == 0, "data_out must reset to 0"
    assert int(dut.o_rw_bit.value) == 1, "rw_bit must reset to READ"
    assert int(dut.o_done.value) == 0, "done must reset low"
    assert int(dut.o_write_enable.value) == 0, "write_enable must reset low"
    assert int(dut.o_rx_frame.value) == 0, "rx_frame must reset to 0"
    assert int(dut.o_miso.value) == 0, "miso must idle low while deselected"
    cocotb.log.info("Reset state OK")


@cocotb.test()
async def test_write_frame_capture(dut):
    await reset_dut(dut)
    for addr, data in [
        (0x00, 0x00),
        (0x10, 0xFF),
        (0x2A, 0x55),
        (0x7F, 0xAA),
        (0x01, 0x80),
        (0x40, 0x7F),
    ]:
        await transfer(dut, RW_WRITE, addr, data)
        assert int(dut.o_addr.value) == addr, (
            f"addr_out expected 0x{addr:02X}, got 0x{int(dut.o_addr.value):02X}"
        )
        assert int(dut.o_data.value) == data, (
            f"data_out expected 0x{data:02X}, got 0x{int(dut.o_data.value):02X}"
        )
        assert int(dut.o_rw_bit.value) == RW_WRITE, "rw_bit must be 0 for a write"
        assert int(dut.o_rx_frame.value) == frame_of(RW_WRITE, addr, data), (
            "rx_frame must hold the complete received frame"
        )
        cocotb.log.info(f"  write addr=0x{addr:02X} data=0x{data:02X} OK")
    cocotb.log.info("Write frame capture OK")


@cocotb.test()
async def test_read_frame_returns_data_in(dut):
    await reset_dut(dut)
    for addr, value in [
        (0x00, 0x00),
        (0x01, 0x01),
        (0x02, 0x5A),
        (0x03, 0xA5),
        (0x06, 0xFF),
        (0x10, 0x80),
        (0x7F, 0x7F),
    ]:
        got = await transfer(dut, RW_READ, addr, 0x00, value)
        assert got == value, (
            f"read at 0x{addr:02X}: expected 0x{value:02X}, got 0x{got:02X}"
        )
        assert int(dut.o_rw_bit.value) == RW_READ, "rw_bit must be 1 for a read"
        cocotb.log.info(f"  read addr=0x{addr:02X} -> 0x{got:02X} OK")
    cocotb.log.info("Read frame returns data_in OK")


@cocotb.test()
async def test_exhaustive_read_values(dut):
    await reset_dut(dut)
    for value in range(256):
        got = await transfer(dut, RW_READ, 0x04, 0x00, value)
        assert got == value, f"expected 0x{value:02X}, got 0x{got:02X}"
    cocotb.log.info("All 256 read values shifted out correctly OK")


@cocotb.test()
async def test_exhaustive_write_data(dut):
    await reset_dut(dut)
    for value in range(256):
        await transfer(dut, RW_WRITE, 0x10, value)
        assert int(dut.o_data.value) == value, (
            f"data_out expected 0x{value:02X}, got 0x{int(dut.o_data.value):02X}"
        )
    cocotb.log.info("All 256 write data values captured correctly OK")


@cocotb.test()
async def test_exhaustive_addresses(dut):
    await reset_dut(dut)
    for addr in range(128):
        await transfer(dut, RW_WRITE, addr, 0x3C)
        assert int(dut.o_addr.value) == addr, (
            f"addr_out expected 0x{addr:02X}, got 0x{int(dut.o_addr.value):02X}"
        )
    cocotb.log.info("All 128 addresses captured correctly OK")


@cocotb.test()
async def test_write_enable_pulse(dut):
    await reset_dut(dut)
    dut.i_data.value = 0x00
    await select(dut)
    seen_write_enable = 0
    frame = frame_of(RW_WRITE, 0x10, 0x07)
    for i in range(FRAME_BITS):
        dut.i_mosi.value = (frame >> (FRAME_BITS - 1 - i)) & 1
        await Timer(HALF_NS, unit="ns")
        dut.i_sclk.value = 1
        await Timer(HALF_NS, unit="ns")
        dut.i_sclk.value = 0
        await Timer(HALF_NS, unit="ns")
        seen_write_enable += int(dut.o_write_enable.value)
    assert seen_write_enable == 1, (
        f"write_enable must pulse exactly once per write frame, "
        f"saw {seen_write_enable}"
    )
    assert int(dut.o_done.value) == 1, "done must be high at the end of the frame"
    await deselect(dut)
    cocotb.log.info("write_enable pulses once per write frame OK")


@cocotb.test()
async def test_no_write_enable_on_read(dut):
    await reset_dut(dut)
    dut.i_data.value = 0x99
    await select(dut)
    seen_write_enable = 0
    frame = frame_of(RW_READ, 0x02, 0x00)
    for i in range(FRAME_BITS):
        dut.i_mosi.value = (frame >> (FRAME_BITS - 1 - i)) & 1
        await Timer(HALF_NS, unit="ns")
        dut.i_sclk.value = 1
        await Timer(HALF_NS, unit="ns")
        dut.i_sclk.value = 0
        await Timer(HALF_NS, unit="ns")
        seen_write_enable += int(dut.o_write_enable.value)
    assert seen_write_enable == 0, (
        f"write_enable must stay low for a read frame, saw {seen_write_enable}"
    )
    await deselect(dut)
    cocotb.log.info("No write_enable during a read frame OK")


@cocotb.test()
async def test_miso_idle_low_when_deselected(dut):
    await reset_dut(dut)
    await transfer(dut, RW_READ, 0x04, 0x00, 0xFF)
    for _ in range(8):
        await Timer(HALF_NS, unit="ns")
        assert int(dut.o_miso.value) == 0, "miso must be driven low while ss_n is high"
    cocotb.log.info("miso idles low while deselected OK")


@cocotb.test()
async def test_back_to_back_frames_same_selection(dut):
    await reset_dut(dut)
    rng = random.Random(41)
    await select(dut)
    for _ in range(20):
        addr = rng.randint(0, 0x7F)
        data = rng.randint(0, 0xFF)
        value = rng.randint(0, 0xFF)
        dut.i_data.value = value
        bits = await shift_frame(dut, frame_of(RW_READ, addr, data))
        assert miso_byte(bits) == value, (
            f"chained read: expected 0x{value:02X}, got 0x{miso_byte(bits):02X}"
        )
        assert int(dut.o_addr.value) == addr
        assert int(dut.o_data.value) == data
    await deselect(dut)
    cocotb.log.info("20 chained frames within a single selection OK")


async def clock_pulse(dut):
    await Timer(HALF_NS, unit="ns")
    dut.i_sclk.value = 1
    await Timer(HALF_NS, unit="ns")
    dut.i_sclk.value = 0
    await Timer(HALF_NS, unit="ns")


async def partial_frame(dut, n_bits):
    await select(dut)
    for _ in range(n_bits):
        dut.i_mosi.value = 1
        await clock_pulse(dut)
    await deselect(dut)


@cocotb.test()
async def test_deselect_resyncs_after_aborted_frame(dut):
    await reset_dut(dut)
    for n_bits in range(1, FRAME_BITS):
        await partial_frame(dut, n_bits)
        await transfer(dut, RW_WRITE, 0x2B, 0xC3)
        assert int(dut.o_addr.value) == 0x2B, (
            f"after aborting at {n_bits} bits, o_addr is "
            f"0x{int(dut.o_addr.value):02X} instead of 0x2B"
        )
        assert int(dut.o_data.value) == 0xC3, (
            f"after aborting at {n_bits} bits, o_data is "
            f"0x{int(dut.o_data.value):02X} instead of 0xC3"
        )
    cocotb.log.info(
        "Deselecting resynchronises the bit counter after an aborted frame, "
        "with no idle clock needed OK"
    )


@cocotb.test()
async def test_aborted_frame_never_forges_a_write(dut):
    await reset_dut(dut)
    rng = random.Random(44)
    for n_bits in range(1, FRAME_BITS):
        for _ in range(20):
            await partial_frame(dut, n_bits)
            addr = rng.randint(0, 0x7F)
            data = rng.randint(0, 0xFF)
            await select(dut)
            bits = await shift_frame(dut, frame_of(RW_READ, addr, data))
            assert int(dut.o_write_enable.value) == 0, (
                f"a read frame after a {n_bits}-bit abort asserted "
                f"o_write_enable"
            )
            await deselect(dut)
            assert int(dut.o_rw_bit.value) == RW_READ, (
                f"a read frame after a {n_bits}-bit abort decoded as a write"
            )
            assert int(dut.o_addr.value) == addr, (
                f"a read frame after a {n_bits}-bit abort decoded address "
                f"0x{int(dut.o_addr.value):02X} instead of 0x{addr:02X}"
            )
            assert miso_byte(bits) is not None
    cocotb.log.info(
        "Read frames issued after an aborted frame can never be decoded as "
        "writes OK"
    )


@cocotb.test()
async def test_complete_frames_never_desync(dut):
    await reset_dut(dut)
    rng = random.Random(43)
    for _ in range(50):
        addr = rng.randint(0, 0x7F)
        data = rng.randint(0, 0xFF)
        await transfer(dut, RW_WRITE, addr, data)
        assert int(dut.o_addr.value) == addr, (
            "complete frames must never desynchronise the slave"
        )
        assert int(dut.o_data.value) == data
    cocotb.log.info("50 complete frames keep the slave synchronised OK")


@cocotb.test()
async def test_random_traffic(dut):
    await reset_dut(dut)
    rng = random.Random(42)
    for _ in range(300):
        rw = rng.randint(0, 1)
        addr = rng.randint(0, 0x7F)
        data = rng.randint(0, 0xFF)
        value = rng.randint(0, 0xFF)
        got = await transfer(dut, rw, addr, data, value)
        assert int(dut.o_addr.value) == addr, (
            f"addr_out expected 0x{addr:02X}, got 0x{int(dut.o_addr.value):02X}"
        )
        assert int(dut.o_data.value) == data, (
            f"data_out expected 0x{data:02X}, got 0x{int(dut.o_data.value):02X}"
        )
        assert int(dut.o_rw_bit.value) == rw
        if rw == RW_READ:
            assert got == value, (
                f"read expected 0x{value:02X}, got 0x{got:02X}"
            )
    cocotb.log.info("300 random frames OK")


@cocotb.test()
async def test_rw_bit_latched_at_header(dut):
    await reset_dut(dut)
    await transfer(dut, RW_WRITE, 0x10, 0x00)
    assert int(dut.o_rw_bit.value) == RW_WRITE
    dut.i_data.value = 0x6D
    await select(dut)
    frame = frame_of(RW_READ, 0x05, 0x00)
    for i in range(FRAME_BITS):
        dut.i_mosi.value = (frame >> (FRAME_BITS - 1 - i)) & 1
        await Timer(HALF_NS, unit="ns")
        dut.i_sclk.value = 1
        await Timer(HALF_NS, unit="ns")
        dut.i_sclk.value = 0
        await Timer(HALF_NS, unit="ns")
        if i == HDR_LAST_BIT:
            assert int(dut.o_rw_bit.value) == RW_READ, (
                "rw_bit must be latched on the last header bit"
            )
            assert int(dut.o_addr.value) == 0x05, (
                "addr_out must be latched on the last header bit"
            )
    await deselect(dut)
    cocotb.log.info("rw_bit and addr_out latch on the header boundary OK")


@cocotb.test()
async def test_reset_during_frame(dut):
    await reset_dut(dut)
    await transfer(dut, RW_WRITE, 0x33, 0x44)
    await select(dut)
    for i in range(6):
        dut.i_mosi.value = 1
        await Timer(HALF_NS, unit="ns")
        dut.i_sclk.value = 1
        await Timer(HALF_NS, unit="ns")
        dut.i_sclk.value = 0
        await Timer(HALF_NS, unit="ns")
    dut.i_rstn.value = 0
    await Timer(HALF_NS * 2, unit="ns")
    dut.i_rstn.value = 1
    await deselect(dut)
    assert int(dut.o_addr.value) == 0, "reset must clear addr_out"
    assert int(dut.o_data.value) == 0, "reset must clear data_out"
    await transfer(dut, RW_WRITE, 0x12, 0x34)
    assert int(dut.o_addr.value) == 0x12
    assert int(dut.o_data.value) == 0x34
    cocotb.log.info("Reset during a frame recovers cleanly OK")
