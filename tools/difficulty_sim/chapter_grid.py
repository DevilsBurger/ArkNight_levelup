"""챕터 배율 강도 × 초기 DP 보정 격자 (D·G1). 예) python3 -I chapter_grid.py 2,3,4,5 200"""
import sys, zlib
from multiprocessing import Pool
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from stagedef_loader import load_stages
from model import load_params, load_policies, load_enemy_table, simulate_cell
P = load_params(); POL = load_policies(); T = load_enemy_table(P)
chs = [int(c) for c in (sys.argv[1] if len(sys.argv) > 1 else "2,3,4,5").split(",")]
runs = int(sys.argv[2]) if len(sys.argv) > 2 else 200
S = [s for s in load_stages() if s.chapter in chs]
GRID = [(m, d) for m in (0.4, 0.6, 0.8, 1.0) for d in (0, 6)]

def cell(a):
    sid, ov, g = a
    sd = next(s for s in S if s.id == sid); growth = P["growth_by_chapter"][sd.chapter]["G1"]
    return (sid, ov, g, simulate_cell(sd, P, POL[g], growth, T, runs, zlib.crc32(f"{sid}{sorted(ov.items())}{g}".encode()) % 2**31, ov))

jobs = [(s.id, {"chapter_scale_mult": m, "initial_dp_add": d}, g) for s in S for (m, d) in GRID for g in ("D",)]
with Pool(4) as pool:
    res = pool.map(cell, jobs)
R = {(sid, ov["chapter_scale_mult"], ov["initial_dp_add"]): r for sid, ov, g, r in res}
for ch in chs:
    ids = [s.id for s in S if s.chapter == ch]
    print(f"\n### {ch}장 D·G1 — P_★3 / P_clear (열: 배율 강도 m, 초기 DP +d)")
    print("| 스테이지 | " + " | ".join(f"m{m} d{d}" for m, d in GRID) + " |")
    print("| :-: | " + " | ".join(":-:" for _ in GRID) + " |")
    for sid in ids:
        print(f"| {sid} | " + " | ".join(f"{R[(sid,m,d)]['P_star3']*100:.0f}/{R[(sid,m,d)]['P_clear']*100:.0f}" for m, d in GRID) + " |")
    print("| 평균 | " + " | ".join(f"{sum(R[(sid,m,d)]['P_star3'] for sid in ids)/len(ids)*100:.0f}/{sum(R[(sid,m,d)]['P_clear'] for sid in ids)/len(ids)*100:.0f}" for m, d in GRID) + " |")
