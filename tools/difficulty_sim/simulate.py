"""몬테카를로 전수 실행 CLI.
예) python3 -I tools/difficulty_sim/simulate.py --runs 300 --policies S,A,B,C,D,E --growth G0,G1,G2
    python3 -I tools/difficulty_sim/simulate.py --set relocate_cd=12 --tag cd12"""
from __future__ import annotations
import argparse, csv, sys, time, zlib
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stagedef_loader import load_stages
from model import load_params, load_policies, load_enemy_table, simulate_cell

FIELDS = ["stage", "name", "policy", "growth", "tag", "runs", "P_clear", "P_star3", "leaks", "knockdowns", "legion_deaths", "relocates",
          "ult_uses", "hero_kill_share", "dp_spent", "dp_kill", "deploys", "retreats", "skill_uses", "T_mean", "lives_left",
          "cause_leak", "cause_boss", "cause_timeout", "civ_alive"]


def cell_seed(base: int, key: str) -> int:
    return (base * 1000003 + zlib.crc32(key.encode())) % (2 ** 31)


def parse_set(items: list[str]) -> dict:
    ov = {}
    for it in items or []:
        k, v = it.split("=", 1)
        ov[k] = float(v)
    return ov


def run_cell(args):
    sd, P, pol_key, pol, g_key, growth, table, runs, seed, ov, tag = args
    m = simulate_cell(sd, P, pol, growth, table, runs, seed, ov)
    row = dict(stage=sd.id, name=sd.name, policy=pol_key, growth=g_key, tag=tag)
    row.update(m)
    return row


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--stages", default="all")
    ap.add_argument("--runs", type=int, default=300)
    ap.add_argument("--policies", default="S,A,B,C,D,E")
    ap.add_argument("--growth", default="G0,G1,G2")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--set", action="append", help="오버라이드 key=value (dp_regen_mult, hero_atk_mult, hero_hp_mult, enemy_hp_mult, enemy_atk_mult, relocate_cd, hero_kill_dp_mult, deploy_limit_add, legion_mult)")
    ap.add_argument("--tag", default="base")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "out" / "results.csv"))
    ap.add_argument("--append", action="store_true")
    a = ap.parse_args(argv)
    P = load_params(); POL = load_policies(); table = load_enemy_table(P)
    stages = load_stages(ids=None if a.stages == "all" else set(a.stages.split(",")))
    ov = parse_set(a.set)
    jobs = []
    for sd in stages:
        for pk in a.policies.split(","):
            for gk in a.growth.split(","):
                jobs.append((sd, P, pk, POL[pk], gk, P["growth_states"][gk], table, a.runs, cell_seed(a.seed, f"{sd.id}|{pk}|{gk}"), ov, a.tag))
    t0 = time.time()
    if a.jobs > 1:
        with Pool(a.jobs) as pool: rows = pool.map(run_cell, jobs)
    else:
        rows = [run_cell(j) for j in jobs]
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if a.append and out.exists() else "w"
    with open(out, mode, newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if mode == "w": w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} cells × {a.runs} runs in {time.time() - t0:.1f}s → {out}")
    return rows


if __name__ == "__main__":
    main()
