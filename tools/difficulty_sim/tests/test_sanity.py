"""sanity · 단조성 · 재현성 테스트. 실행: python3 -I tools/difficulty_sim/tests/test_sanity.py"""
from __future__ import annotations
import sys, copy
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from stagedef_loader import load_stages
from model import load_params, load_policies, load_enemy_table, simulate_cell, Sim

P = load_params(); POL = load_policies(); T = load_enemy_table(P)
S = {s.id: s for s in load_stages()}
G = P["growth_states"]


def cell(sid, pol, g, runs=40, ov=None, seed=1):
    return simulate_cell(S[sid], P, POL[pol], G[g], T, runs, seed, ov)


def test_no_enemies_clears():
    sd = copy.deepcopy(S["1-4"]); sd.waves = [dict(t=1, enemy="E01", route="A", count=1, interval=0)]
    m = simulate_cell(sd, P, POL["D"], G["G1"], T, 20, 3)
    assert m["P_clear"] == 1.0, m


def test_overwhelming_enemies_fail():
    m = cell("1-4", "D", "G0", ov={"enemy_hp_mult": 50.0, "enemy_atk_mult": 10.0})
    assert m["P_clear"] < 0.2, m


def test_deterministic_same_seed():
    a = Sim(S["1-6"], P, POL["D"], G["G1"], T, 7).run(); b = Sim(S["1-6"], P, POL["D"], G["G1"], T, 7).run()
    assert a == b


def test_monotone_enemy_hp():
    lo = cell("1-6", "D", "G1", ov={"enemy_hp_mult": 0.5})["P_clear"]
    hi = cell("1-6", "D", "G1", ov={"enemy_hp_mult": 2.5})["P_clear"]
    assert lo >= hi, (lo, hi)


def test_solo_designed_stage():
    m = cell("1-3", "S", "G0")
    assert m["P_clear"] > 0.5, m


def test_hero_no_damage_no_legion_fails():
    m = cell("1-4", "S", "G0", ov={"hero_atk_mult": 0.0})
    assert m["P_clear"] < 0.2, m


if __name__ == "__main__":
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            try:
                fn(); print("ok  ", name)
            except AssertionError as e:
                fails += 1; print("FAIL", name, e)
    sys.exit(1 if fails else 0)
