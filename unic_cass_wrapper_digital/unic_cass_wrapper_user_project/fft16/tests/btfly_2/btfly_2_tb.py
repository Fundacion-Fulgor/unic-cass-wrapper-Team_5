import random

import cocotb
from cocotb.triggers import Timer

NB_INPUT = 8
NB_OUTPUT = NB_INPUT + 1

IN_MIN = -(1 << (NB_INPUT - 1))
IN_MAX = (1 << (NB_INPUT - 1)) - 1
OUT_MIN = -(1 << (NB_OUTPUT - 1))
OUT_MAX = (1 << (NB_OUTPUT - 1)) - 1

CORNERS = [IN_MIN, IN_MIN + 1, -64, -1, 0, 1, 64, IN_MAX - 1, IN_MAX]


def to_signed(value, bits):
    value = int(value) & ((1 << bits) - 1)
    if value >= (1 << (bits - 1)):
        value -= 1 << bits
    return value


async def apply(dut, a_r, a_i, b_r, b_i):
    dut.i_data0_r.value = a_r & ((1 << NB_INPUT) - 1)
    dut.i_data0_i.value = a_i & ((1 << NB_INPUT) - 1)
    dut.i_data1_r.value = b_r & ((1 << NB_INPUT) - 1)
    dut.i_data1_i.value = b_i & ((1 << NB_INPUT) - 1)
    await Timer(1, unit="ns")
    return (
        to_signed(dut.o_data0_r.value, NB_OUTPUT),
        to_signed(dut.o_data0_i.value, NB_OUTPUT),
        to_signed(dut.o_data1_r.value, NB_OUTPUT),
        to_signed(dut.o_data1_i.value, NB_OUTPUT),
    )


async def check(dut, a_r, a_i, b_r, b_i):
    got = await apply(dut, a_r, a_i, b_r, b_i)
    exp = (a_r + b_r, a_i + b_i, a_r - b_r, a_i - b_i)
    assert got == exp, (
        f"inputs a=({a_r},{a_i}) b=({b_r},{b_i}): expected {exp}, got {got}"
    )
    return got


@cocotb.test()
async def test_exhaustive_real_pair(dut):
    count = 0
    for a_r in range(IN_MIN, IN_MAX + 1):
        for b_r in range(IN_MIN, IN_MAX + 1):
            got = await apply(dut, a_r, 0, b_r, 0)
            assert got[0] == a_r + b_r, (
                f"o_data0_r: {a_r}+{b_r} expected {a_r + b_r}, got {got[0]}"
            )
            assert got[2] == a_r - b_r, (
                f"o_data1_r: {a_r}-{b_r} expected {a_r - b_r}, got {got[2]}"
            )
            count += 1
    cocotb.log.info(f"Exhaustive real pair sweep: {count} combinations OK")


@cocotb.test()
async def test_exhaustive_imag_pair(dut):
    count = 0
    for a_i in range(IN_MIN, IN_MAX + 1):
        for b_i in range(IN_MIN, IN_MAX + 1):
            got = await apply(dut, 0, a_i, 0, b_i)
            assert got[1] == a_i + b_i, (
                f"o_data0_i: {a_i}+{b_i} expected {a_i + b_i}, got {got[1]}"
            )
            assert got[3] == a_i - b_i, (
                f"o_data1_i: {a_i}-{b_i} expected {a_i - b_i}, got {got[3]}"
            )
            count += 1
    cocotb.log.info(f"Exhaustive imag pair sweep: {count} combinations OK")


@cocotb.test()
async def test_all_corner_combinations(dut):
    count = 0
    for a_r in CORNERS:
        for a_i in CORNERS:
            for b_r in CORNERS:
                for b_i in CORNERS:
                    await check(dut, a_r, a_i, b_r, b_i)
                    count += 1
    cocotb.log.info(f"Corner combinations: {count} vectors OK")


@cocotb.test()
async def test_random_vectors(dut):
    random.seed(7)
    for _ in range(5000):
        await check(
            dut,
            random.randint(IN_MIN, IN_MAX),
            random.randint(IN_MIN, IN_MAX),
            random.randint(IN_MIN, IN_MAX),
            random.randint(IN_MIN, IN_MAX),
        )
    cocotb.log.info("5000 random vectors OK")


@cocotb.test()
async def test_no_output_overflow(dut):
    random.seed(8)
    vectors = [(a, b) for a in CORNERS for b in CORNERS]
    vectors += [
        (random.randint(IN_MIN, IN_MAX), random.randint(IN_MIN, IN_MAX))
        for _ in range(2000)
    ]
    for a, b in vectors:
        got = await apply(dut, a, a, b, b)
        for value in got:
            assert OUT_MIN <= value <= OUT_MAX, (
                f"output {value} outside {NB_OUTPUT}-bit signed range "
                f"for a={a} b={b}"
            )
    cocotb.log.info(f"{len(vectors)} vectors stay within the widened output range OK")


@cocotb.test()
async def test_paths_independent(dut):
    random.seed(9)
    for _ in range(1000):
        a_r = random.randint(IN_MIN, IN_MAX)
        a_i = random.randint(IN_MIN, IN_MAX)
        b_r = random.randint(IN_MIN, IN_MAX)
        b_i = random.randint(IN_MIN, IN_MAX)
        full = await apply(dut, a_r, a_i, b_r, b_i)
        only_real = await apply(dut, a_r, 0, b_r, 0)
        only_imag = await apply(dut, 0, a_i, 0, b_i)
        assert full[0] == only_real[0] and full[2] == only_real[2], (
            "real outputs depend on the imaginary inputs"
        )
        assert full[1] == only_imag[1] and full[3] == only_imag[3], (
            "imaginary outputs depend on the real inputs"
        )
    cocotb.log.info("Real and imaginary paths are independent OK")


@cocotb.test()
async def test_butterfly_identities(dut):
    random.seed(10)
    for _ in range(1000):
        a_r = random.randint(IN_MIN, IN_MAX)
        a_i = random.randint(IN_MIN, IN_MAX)
        b_r = random.randint(IN_MIN, IN_MAX)
        b_i = random.randint(IN_MIN, IN_MAX)
        s_r, s_i, d_r, d_i = await apply(dut, a_r, a_i, b_r, b_i)
        assert s_r + d_r == 2 * a_r, "sum+diff must equal twice the first real input"
        assert s_i + d_i == 2 * a_i, "sum+diff must equal twice the first imag input"
        assert s_r - d_r == 2 * b_r, "sum-diff must equal twice the second real input"
        assert s_i - d_i == 2 * b_i, "sum-diff must equal twice the second imag input"
        sw_r, sw_i, swd_r, swd_i = await apply(dut, b_r, b_i, a_r, a_i)
        assert (sw_r, sw_i) == (s_r, s_i), "sum output must be commutative"
        assert (swd_r, swd_i) == (-d_r, -d_i), "difference must negate when swapped"
    cocotb.log.info("Butterfly algebraic identities hold OK")


@cocotb.test()
async def test_zero_inputs(dut):
    got = await apply(dut, 0, 0, 0, 0)
    assert got == (0, 0, 0, 0), f"zero input must give zero output, got {got}"
    for v in CORNERS:
        got = await check(dut, v, v, 0, 0)
        assert got[0] == v and got[2] == v
        got = await check(dut, 0, 0, v, v)
        assert got[0] == v and got[2] == -v
    cocotb.log.info("Zero input handling OK")
