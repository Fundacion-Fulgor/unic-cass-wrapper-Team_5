import random

import cocotb
from cocotb.triggers import Timer

from model_clip_round import ClipRoundConfig, ROUND, to_signed

CONFIGS = {
    0: ClipRoundConfig(32, 30, 16, 15, 1),
    1: ClipRoundConfig(12, 6, 8, 3, 0),
    2: ClipRoundConfig(12, 7, 8, 6, 0),
    3: ClipRoundConfig(21, 15, 10, 6, 1),
    4: ClipRoundConfig(21, 12, 10, 3, 1),
    5: ClipRoundConfig(8, 4, 5, 2, 0),
    6: ClipRoundConfig(8, 4, 5, 2, 1),
    7: ClipRoundConfig(10, 6, 6, 3, 1),
    8: ClipRoundConfig(8, 6, 8, 6, 1),
}

EXHAUSTIVE_CFGS = [5, 6, 7, 8]
SMALL_CFGS = [1, 2, 5, 6, 7, 8]


def port_in(dut, idx, part):
    return getattr(dut, f"i_{part}{idx}")


def port_out(dut, idx, part):
    return getattr(dut, f"o_{part}{idx}")


async def drive(dut, idx, re_val, im_val):
    cfg = CONFIGS[idx]
    port_in(dut, idx, "re").value = re_val & ((1 << cfg.nb_inp) - 1)
    port_in(dut, idx, "im").value = im_val & ((1 << cfg.nb_inp) - 1)
    await Timer(1, unit="ns")
    got_re = to_signed(port_out(dut, idx, "re").value, cfg.nb_out)
    got_im = to_signed(port_out(dut, idx, "im").value, cfg.nb_out)
    return got_re, got_im


async def check(dut, idx, re_val, im_val):
    cfg = CONFIGS[idx]
    got_re, got_im = await drive(dut, idx, re_val, im_val)
    exp_re = cfg.apply(re_val)
    exp_im = cfg.apply(im_val)
    assert got_re == exp_re, (
        f"cfg{idx} re: in={re_val} expected {exp_re}, got {got_re}"
    )
    assert got_im == exp_im, (
        f"cfg{idx} im: in={im_val} expected {exp_im}, got {got_im}"
    )
    return got_re, got_im


def full_range(cfg):
    return range(cfg.in_min, cfg.in_max + 1)


def boundary_values(cfg):
    anchors = [
        cfg.in_min,
        cfg.in_min + 1,
        -1,
        0,
        1,
        cfg.in_max - 1,
        cfg.in_max,
        cfg.sat_low_int(),
        cfg.sat_high_int(),
    ]
    vals = set()
    for a in anchors:
        for d in range(-3, 4):
            v = a + d
            if cfg.in_min <= v <= cfg.in_max:
                vals.add(v)
    step = 1 << cfg.bits_dis if cfg.bits_dis > 0 else 1
    for k in range(-8, 9):
        for d in (-1, 0, 1):
            v = k * step + d
            if cfg.in_min <= v <= cfg.in_max:
                vals.add(v)
    return sorted(vals)


@cocotb.test()
async def test_exhaustive_small_configs(dut):
    for idx in EXHAUSTIVE_CFGS:
        cfg = CONFIGS[idx]
        values = list(full_range(cfg))
        count = 0
        for re_val in values:
            im_val = values[len(values) - 1 - values.index(re_val)]
            await check(dut, idx, re_val, im_val)
            count += 1
        cocotb.log.info(
            f"cfg{idx} Q({cfg.nb_inp},{cfg.nbf_inp})->Q({cfg.nb_out},{cfg.nbf_out}) "
            f"RND_MD={cfg.rnd_md}: {count} exhaustive input values OK"
        )


@cocotb.test()
async def test_saturation_boundaries(dut):
    for idx, cfg in CONFIGS.items():
        for v in boundary_values(cfg):
            await check(dut, idx, v, -v if cfg.in_min <= -v <= cfg.in_max else v)
        cocotb.log.info(f"cfg{idx}: {len(boundary_values(cfg))} boundary values OK")


@cocotb.test()
async def test_saturation_clamps_extremes(dut):
    for idx, cfg in CONFIGS.items():
        got_re, got_im = await drive(dut, idx, cfg.in_max, cfg.in_min)
        if cfg.sat_high_int() < cfg.in_max:
            assert got_re == cfg.out_max, (
                f"cfg{idx}: max input must saturate high, got {got_re}"
            )
        if cfg.sat_low_int() > cfg.in_min:
            assert got_im == cfg.out_min, (
                f"cfg{idx}: min input must saturate low, got {got_im}"
            )
        cocotb.log.info(f"cfg{idx}: extremes re={got_re} im={got_im} OK")


@cocotb.test()
async def test_output_within_range(dut):
    random.seed(1)
    for idx, cfg in CONFIGS.items():
        for _ in range(300):
            re_val = random.randint(cfg.in_min, cfg.in_max)
            im_val = random.randint(cfg.in_min, cfg.in_max)
            got_re, got_im = await check(dut, idx, re_val, im_val)
            assert cfg.out_min <= got_re <= cfg.out_max
            assert cfg.out_min <= got_im <= cfg.out_max
        cocotb.log.info(f"cfg{idx}: 300 random values in range OK")


@cocotb.test()
async def test_quantisation_error_bound(dut):
    random.seed(2)
    for idx, cfg in CONFIGS.items():
        lsb = cfg.lsb_out()
        limit = lsb if cfg.rnd_md == 0 else 0.5 * lsb
        for _ in range(300):
            v = random.randint(cfg.sat_low_int(), cfg.sat_high_int())
            got_re, got_im = await check(dut, idx, v, v)
            err = abs(cfg.out_float(got_re) - cfg.ideal_float(v))
            assert err <= limit + 1e-12, (
                f"cfg{idx}: quantisation error {err} exceeds {limit} for input {v}"
            )
        cocotb.log.info(f"cfg{idx}: error bound {limit:.3e} respected OK")


@cocotb.test()
async def test_monotonicity(dut):
    for idx in SMALL_CFGS:
        cfg = CONFIGS[idx]
        prev = None
        for v in full_range(cfg):
            got_re, _ = await drive(dut, idx, v, 0)
            if prev is not None:
                assert got_re >= prev, (
                    f"cfg{idx}: output not monotonic at input {v}: {prev} -> {got_re}"
                )
            prev = got_re
        cocotb.log.info(f"cfg{idx}: monotonic across full input range OK")


@cocotb.test()
async def test_zero_and_sign_symmetry(dut):
    for idx, cfg in CONFIGS.items():
        got_re, got_im = await check(dut, idx, 0, 0)
        assert got_re == 0 and got_im == 0, f"cfg{idx}: zero input must give zero"
        for mag in [1, 2, 3, 5, 8, 13, 21]:
            v = mag << max(cfg.bits_dis, 0)
            if v > cfg.sat_high_int():
                continue
            pos_re, _ = await drive(dut, idx, v, 0)
            neg_re, _ = await drive(dut, idx, -v, 0)
            assert pos_re == -neg_re, (
                f"cfg{idx}: expected symmetry for +/-{v}, got {pos_re} and {neg_re}"
            )
        cocotb.log.info(f"cfg{idx}: zero and sign symmetry OK")


@cocotb.test()
async def test_re_im_paths_independent(dut):
    random.seed(3)
    for idx, cfg in CONFIGS.items():
        for _ in range(100):
            re_val = random.randint(cfg.in_min, cfg.in_max)
            im_val = random.randint(cfg.in_min, cfg.in_max)
            both_re, both_im = await drive(dut, idx, re_val, im_val)
            only_re, _ = await drive(dut, idx, re_val, 0)
            _, only_im = await drive(dut, idx, 0, im_val)
            assert both_re == only_re, f"cfg{idx}: re path depends on im input"
            assert both_im == only_im, f"cfg{idx}: im path depends on re input"
        cocotb.log.info(f"cfg{idx}: re/im paths independent OK")


@cocotb.test()
async def test_against_golden_model(dut):
    random.seed(4)
    round_model = ROUND()
    for idx, cfg in CONFIGS.items():
        mode = "around" if cfg.rnd_md == 1 else "floor"
        for _ in range(400):
            v = random.randint(cfg.in_min, cfg.in_max)
            got_re, _ = await drive(dut, idx, v, 0)
            expected = round_model.crnd(
                complex(cfg.ideal_float(v), 0.0),
                True,
                cfg.nb_out,
                cfg.nbf_out,
                mode,
            )
            assert abs(cfg.out_float(got_re) - expected.real) < 1e-12, (
                f"cfg{idx}: golden model expected {expected.real}, "
                f"got {cfg.out_float(got_re)} for input {v}"
            )
        cocotb.log.info(f"cfg{idx}: 400 values match the golden ROUND model OK")


@cocotb.test()
async def test_ties_round_to_even(dut):
    round_model = ROUND()
    for idx, cfg in CONFIGS.items():
        if cfg.bits_dis == 0:
            continue
        step = 1 << cfg.bits_dis
        half = step // 2
        ties = [
            k * step + half
            for k in range(-24, 25)
            if cfg.in_min <= k * step + half <= cfg.in_max
        ]
        assert ties, f"cfg{idx}: no tie values in range"
        mode = "around" if cfg.rnd_md == 1 else "floor"
        for v in ties:
            got_re, got_im = await drive(dut, idx, v, -v)
            expected = round_model.crnd(
                complex(cfg.ideal_float(v), cfg.ideal_float(-v)),
                True,
                cfg.nb_out,
                cfg.nbf_out,
                mode,
            )
            assert abs(cfg.out_float(got_re) - expected.real) < 1e-12, (
                f"cfg{idx}: tie at {v} gave {cfg.out_float(got_re)}, "
                f"golden model says {expected.real}"
            )
            assert abs(cfg.out_float(got_im) - expected.imag) < 1e-12, (
                f"cfg{idx}: tie at {-v} gave {cfg.out_float(got_im)}, "
                f"golden model says {expected.imag}"
            )
            if cfg.rnd_md == 1 and cfg.out_min < got_re < cfg.out_max:
                assert got_re % 2 == 0, (
                    f"cfg{idx}: tie at {v} rounded to the odd value {got_re}"
                )
        cocotb.log.info(
            f"cfg{idx}: {len(ties)} exact ties resolve to the even neighbour OK"
        )


@cocotb.test()
async def test_ties_follow_the_even_rule(dut):
    for idx, cfg in CONFIGS.items():
        if cfg.rnd_md != 1 or cfg.bits_dis == 0:
            continue
        step = 1 << cfg.bits_dis
        half = step // 2
        up = 0
        down = 0
        for k in range(-40, 41):
            v = k * step + half
            if not (cfg.sat_low_int() <= v <= cfg.sat_high_int()):
                continue
            truncated = v >> cfg.bits_dis
            want = truncated + (truncated & 1)
            if not (cfg.out_min <= want <= cfg.out_max):
                continue
            got_re, _ = await drive(dut, idx, v, 0)
            assert got_re == want, (
                f"cfg{idx}: tie at {v} truncates to {truncated}, so round to "
                f"even wants {want}, got {got_re}"
            )
            if got_re == truncated + 1:
                up += 1
            else:
                down += 1
        assert up > 0 and down > 0, (
            f"cfg{idx}: ties never alternate, {up} up and {down} down"
        )
        assert abs(up - down) <= 1, (
            f"cfg{idx}: ties do not alternate evenly, {up} up and {down} down"
        )
        cocotb.log.info(
            f"cfg{idx}: every tie lands on the even neighbour, {up} up and "
            f"{down} down OK"
        )
