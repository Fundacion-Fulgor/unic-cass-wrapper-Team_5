import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

from model_fft4 import FFT4_Reference

CLK_NS = 10
NB_INPUT = 8
NBF_INPUT = 6
NB_STG1 = NB_INPUT + 1
NB_STG2 = NB_INPUT + 2
DESIGN_GAP = 7

IN_MIN = -(1 << (NB_INPUT - 1))
IN_MAX = (1 << (NB_INPUT - 1)) - 1


def to_signed(value, bits):
    value = int(value) & ((1 << bits) - 1)
    if value >= (1 << (bits - 1)):
        value -= 1 << bits
    return value


def rotate(value, inverse):
    if inverse:
        return complex(-value.imag, value.real)
    return complex(value.imag, -value.real)


def model_stages(block, inverse):
    b0, b1, b2, b3 = block
    v0 = b0 + b2
    v1 = b0 - b2
    v2 = b1 + b3
    v3 = rotate(b1 - b3, inverse)
    return [v0, v1, v2, v3], [v0 + v2, v1 + v3, v0 - v2, v1 - v3]


class Recorder:
    def __init__(self, dut, valid_sig, ports, bits):
        self.dut = dut
        self.valid_sig = valid_sig
        self.ports = ports
        self.bits = bits
        self.captured = []
        self.running = True

    def start(self):
        self.task = cocotb.start_soon(self._run())
        return self

    async def _run(self):
        while self.running:
            await RisingEdge(self.dut.i_clk)
            if self.valid_sig.value == 1:
                self.captured.append(
                    (
                        complex(
                            to_signed(self.ports[0].value, self.bits),
                            to_signed(self.ports[1].value, self.bits),
                        ),
                        complex(
                            to_signed(self.ports[2].value, self.bits),
                            to_signed(self.ports[3].value, self.bits),
                        ),
                    )
                )

    async def stop(self, drain=8):
        for _ in range(drain):
            await RisingEdge(self.dut.i_clk)
        self.running = False
        await RisingEdge(self.dut.i_clk)
        return self.captured


def stage1_recorder(dut):
    return Recorder(
        dut,
        dut.u_fft4_mdc_stage1.o_valid,
        [dut.stg1_1r, dut.stg1_1i, dut.stg1_2r, dut.stg1_2i],
        NB_STG1,
    )


def stage2_recorder(dut):
    return Recorder(
        dut,
        dut.o_valid,
        [dut.o_data1_r, dut.o_data1_i, dut.o_data2_r, dut.o_data2_i],
        NB_STG2,
    )


async def reset_dut(dut, inverse=0):
    dut.i_rstn.value = 0
    dut.i_inverse.value = inverse
    dut.i_valid.value = 0
    dut.i_data1_r.value = 0
    dut.i_data1_i.value = 0
    dut.i_data2_r.value = 0
    dut.i_data2_i.value = 0
    for _ in range(4):
        await RisingEdge(dut.i_clk)
    dut.i_rstn.value = 1
    await RisingEdge(dut.i_clk)


async def start(dut, inverse=0):
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    await reset_dut(dut, inverse)


async def push(dut, first, second, gap=DESIGN_GAP):
    mask = (1 << NB_INPUT) - 1
    dut.i_valid.value = 1
    dut.i_data1_r.value = int(first.real) & mask
    dut.i_data1_i.value = int(first.imag) & mask
    dut.i_data2_r.value = int(second.real) & mask
    dut.i_data2_i.value = int(second.imag) & mask
    await RisingEdge(dut.i_clk)
    dut.i_valid.value = 0
    dut.i_data1_r.value = 0
    dut.i_data1_i.value = 0
    dut.i_data2_r.value = 0
    dut.i_data2_i.value = 0
    for _ in range(gap):
        await RisingEdge(dut.i_clk)


async def run_blocks(dut, blocks, gap=DESIGN_GAP):
    rec1 = stage1_recorder(dut).start()
    rec2 = stage2_recorder(dut).start()
    for block in blocks:
        await push(dut, block[0], block[2], gap)
        await push(dut, block[1], block[3], gap)
    captured1 = await rec1.stop()
    captured2 = await rec2.stop()
    return captured1, captured2


def unpack(captured):
    blocks = []
    for idx in range(0, len(captured), 2):
        first, second = captured[idx], captured[idx + 1]
        blocks.append([first[0], second[0], first[1], second[1]])
    return blocks


def random_block(rng):
    return [
        complex(rng.randint(IN_MIN, IN_MAX), rng.randint(IN_MIN, IN_MAX))
        for _ in range(4)
    ]


def check_blocks(blocks, captured1, captured2, inverse):
    got1 = unpack(captured1)
    got2 = unpack(captured2)
    assert len(got1) == len(blocks), (
        f"stage1 produced {len(got1)} blocks, expected {len(blocks)}"
    )
    assert len(got2) == len(blocks), (
        f"stage2 produced {len(got2)} blocks, expected {len(blocks)}"
    )
    for idx, block in enumerate(blocks):
        exp1, exp2 = model_stages(block, inverse)
        assert got1[idx] == exp1, (
            f"block {idx} stage1: expected {exp1}, got {got1[idx]}"
        )
        assert got2[idx] == exp2, (
            f"block {idx} stage2: expected {exp2}, got {got2[idx]}"
        )


@cocotb.test()
async def test_single_block_fft(dut):
    await start(dut, inverse=0)
    rng = random.Random(61)
    blocks = [random_block(rng)]
    captured1, captured2 = await run_blocks(dut, blocks)
    check_blocks(blocks, captured1, captured2, inverse=0)
    cocotb.log.info("Single FFT block through both MDC stages OK")


@cocotb.test()
async def test_single_block_ifft(dut):
    await start(dut, inverse=1)
    rng = random.Random(62)
    blocks = [random_block(rng)]
    captured1, captured2 = await run_blocks(dut, blocks)
    check_blocks(blocks, captured1, captured2, inverse=1)
    cocotb.log.info("Single IFFT block through both MDC stages OK")


@cocotb.test()
async def test_many_random_blocks_fft(dut):
    await start(dut, inverse=0)
    rng = random.Random(63)
    blocks = [random_block(rng) for _ in range(200)]
    captured1, captured2 = await run_blocks(dut, blocks)
    check_blocks(blocks, captured1, captured2, inverse=0)
    cocotb.log.info(f"{len(blocks)} random FFT blocks OK")


@cocotb.test()
async def test_many_random_blocks_ifft(dut):
    await start(dut, inverse=1)
    rng = random.Random(64)
    blocks = [random_block(rng) for _ in range(200)]
    captured1, captured2 = await run_blocks(dut, blocks)
    check_blocks(blocks, captured1, captured2, inverse=1)
    cocotb.log.info(f"{len(blocks)} random IFFT blocks OK")


@cocotb.test()
async def test_no_stall_across_blocks(dut):
    await start(dut, inverse=0)
    rng = random.Random(65)
    for idx in range(30):
        blocks = [random_block(rng)]
        captured1, captured2 = await run_blocks(dut, blocks)
        assert len(captured2) == 2, (
            f"block {idx} produced {len(captured2)} output pulses instead of 2"
        )
        check_blocks(blocks, captured1, captured2, inverse=0)
    cocotb.log.info("Every block keeps producing exactly 2 output pulses OK")


@cocotb.test()
async def test_varying_gaps(dut):
    rng = random.Random(66)
    for gap in [1, 2, 3, 5, 7, 15]:
        await start(dut, inverse=0)
        blocks = [random_block(rng) for _ in range(8)]
        captured1, captured2 = await run_blocks(dut, blocks, gap=gap)
        check_blocks(blocks, captured1, captured2, inverse=0)
        cocotb.log.info(f"gap={gap} cycles between valid pulses OK")


@cocotb.test()
async def test_extreme_values(dut):
    await start(dut, inverse=0)
    extremes = [IN_MIN, IN_MIN + 1, -1, 0, 1, IN_MAX - 1, IN_MAX]
    blocks = []
    for a in extremes:
        for b in extremes:
            blocks.append(
                [complex(a, b), complex(b, a), complex(-1 - a, b), complex(a, -1 - b)]
            )
    captured1, captured2 = await run_blocks(dut, blocks)
    check_blocks(blocks, captured1, captured2, inverse=0)
    cocotb.log.info(f"{len(blocks)} extreme value blocks with no overflow OK")


@cocotb.test()
async def test_zero_input(dut):
    await start(dut, inverse=0)
    blocks = [[complex(0, 0)] * 4 for _ in range(4)]
    captured1, captured2 = await run_blocks(dut, blocks)
    for pair in captured1 + captured2:
        assert pair == (complex(0, 0), complex(0, 0)), (
            f"zero input must give zero output, got {pair}"
        )
    cocotb.log.info("Zero input gives zero output OK")


@cocotb.test()
async def test_rotation_only_on_second_pulse(dut):
    for inverse in (0, 1):
        await start(dut, inverse=inverse)
        blocks = [[complex(64, 0), complex(64, 0), complex(0, 0), complex(0, 0)]]
        captured1, _ = await run_blocks(dut, blocks)
        got = unpack(captured1)[0]
        assert got[0] == complex(64, 0), "first butterfly must not be rotated"
        assert got[1] == complex(64, 0), "first butterfly difference must not rotate"
        expected_v3 = rotate(complex(64, 0), inverse)
        assert got[3] == expected_v3, (
            f"inverse={inverse}: second pulse difference must be rotated to "
            f"{expected_v3}, got {got[3]}"
        )
        cocotb.log.info(f"inverse={inverse}: rotation applied only to v3 OK")


@cocotb.test()
async def test_mode_switch_between_blocks(dut):
    await start(dut, inverse=0)
    rng = random.Random(67)
    for inverse in [0, 1, 0, 1, 1, 0]:
        await reset_dut(dut, inverse)
        blocks = [random_block(rng) for _ in range(4)]
        captured1, captured2 = await run_blocks(dut, blocks)
        check_blocks(blocks, captured1, captured2, inverse=inverse)
    cocotb.log.info("Switching between FFT and IFFT between blocks OK")


@cocotb.test()
async def test_reset_midblock(dut):
    await start(dut, inverse=0)
    rng = random.Random(68)
    partial = random_block(rng)
    await push(dut, partial[0], partial[2])
    await reset_dut(dut, 0)
    blocks = [random_block(rng) for _ in range(4)]
    captured1, captured2 = await run_blocks(dut, blocks)
    check_blocks(blocks, captured1, captured2, inverse=0)
    cocotb.log.info("Reset after a half-delivered block realigns the MDC OK")


@cocotb.test()
async def test_idle_produces_no_output(dut):
    await start(dut, inverse=0)
    for _ in range(200):
        await RisingEdge(dut.i_clk)
        assert dut.o_valid.value == 0, "o_valid asserted without any input"
    cocotb.log.info("No output while idle OK")


@cocotb.test()
async def test_against_reference_model(dut):
    rng = random.Random(69)
    for inverse in (0, 1):
        await start(dut, inverse=inverse)
        model = FFT4_Reference(
            NB_INPUT=NB_INPUT, NBF_INPUT=NBF_INPUT, inverse=bool(inverse)
        )
        scale = 2 ** NBF_INPUT
        for _ in range(50):
            block = random_block(rng)
            captured1, captured2 = await run_blocks(dut, [block])
            got1, got2 = unpack(captured1)[0], unpack(captured2)[0]
            block_float = [complex(v.real / scale, v.imag / scale) for v in block]
            exp1, exp2 = model.process(block_float)
            for idx in range(4):
                assert abs(got1[idx].real / scale - exp1[idx].real) < 1e-9
                assert abs(got1[idx].imag / scale - exp1[idx].imag) < 1e-9
                assert abs(got2[idx].real / scale - exp2[idx].real) < 1e-9
                assert abs(got2[idx].imag / scale - exp2[idx].imag) < 1e-9
        cocotb.log.info(f"inverse={inverse}: matches the fxpmath reference model OK")
