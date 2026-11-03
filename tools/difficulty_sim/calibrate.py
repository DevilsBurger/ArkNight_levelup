"""보정 격자 탐색: 적 HP · 적 ATK · 주인공 ATK 배율 조합별로 목표 지표를 계산한다.
예) python3 -I calibrate.py --runs 400"""
from __future__ import annotations
import argparse, itertools, sys, time, zlib
from multiprocessing import Pool
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from stagedef_loader import load_stages
from model import load_params, load_policies, load_enemy_table, simulate_cell

P = load_params(); POL = load_policies(); T = load_enemy_table(P); G = P["growth_states"]
STAGES = load_stages()


def cell(args):
    sid, pol, g, runs, ov = args
    sd = next(s for s in STAGES if s.id == sid)
    seed = zlib.crc32(f"{sid}|{pol}|{g}|{sorted(ov.items())}".encode()) % (2 ** 31)
    return (sid, pol, simulate_cell(sd, P, POL[pol], G[g], T, runs, seed, ov))


def evaluate(ov: dict, runs: int, pool) -> dict:
    jobs = [(s.id, pol, "G1", runs, ov) for s in STAGES for pol in ("D", "S", "A")]
    res = {(sid, pol): m for sid, pol, m in pool.map(cell, jobs)}
    d_star = {s.id: res[(s.id, "D")]["P_star3"] for s in STAGES}
    d_clear = {s.id: res[(s.id, "D")]["P_clear"] for s in STAGES}
    solo = {s.id: res[(s.id, "S")]["P_star3"] for s in STAGES}
    a_clear = {s.id: res[(s.id, "A")]["P_clear"] for s in STAGES}
    late = [d_star[s] for s in ("1-4", "1-5", "1-6", "1-7")]
    return dict(ov=ov, d_star=d_star, d_clear=d_clear, solo=solo, a_clear=a_clear,
                d_late_mean=sum(late) / len(late), boss=d_star["1-8"], boss_clear=d_clear["1-8"],
                solo_over20=sum(1 for s in ("1-4", "1-5", "1-6", "1-7", "1-8") if solo[s] > 0.2),
                a_early=sum(a_clear[s] for s in ("1-1", "1-2", "1-3", "1-4")) / 4,
                kd=sum(res[(s.id, "D")]["knockdowns"] for s in STAGES), ld=sum(res[(s.id, "D")]["legion_deaths"] for s in STAGES))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=400)
    ap.add_argument("--hp", default="1.5,2.0,2.5,3.0")
    ap.add_argument("--atk", default="1.5,2.5")
    ap.add_argument("--hero", default="1.0,0.8")
    ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args()
    grid = list(itertools.product([float(x) for x in a.hp.split(",")], [float(x) for x in a.atk.split(",")], [float(x) for x in a.hero.split(",")]))
    t0 = time.time()
    print("| 적HP | 적ATK | 주인공ATK | D★3 1-4~1-7 평균 | D★3 보스 | D클리어 보스 | 솔로★3>20% (1-4~1-8 중) | A 클리어 1-1~1-4 | 넉다운 합 | 군단 이탈 합 | D★3 per stage |")
    print("| :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :--- |")
    with Pool(a.jobs) as pool:
        for hp, atk, hero in grid:
            ov = {"enemy_hp_mult": hp, "enemy_atk_mult": atk, "hero_atk_mult": hero}
            r = evaluate(ov, a.runs, pool)
            per = " ".join(f"{s}:{r['d_star'][s]*100:.0f}" for s in r["d_star"])
            print(f"| {hp} | {atk} | {hero} | {r['d_late_mean']*100:.0f}% | {r['boss']*100:.0f}% | {r['boss_clear']*100:.0f}% | {r['solo_over20']}/5 | {r['a_early']*100:.0f}% | {r['kd']:.2f} | {r['ld']:.2f} | {per} |", flush=True)
    print(f"({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
