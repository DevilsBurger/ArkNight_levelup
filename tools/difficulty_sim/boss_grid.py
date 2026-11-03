"""적 배율 후보 × 보스 변형 후보 탐색 (D · S · A, G0 · G1)."""
import sys, zlib, itertools
from multiprocessing import Pool
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from stagedef_loader import load_stages
from model import load_params, load_policies, load_enemy_table, simulate_cell
P = load_params(); POL = load_policies(); T = load_enemy_table(P); G = P["growth_states"]; S = load_stages()

def cell(a):
    sid, pol, g, runs, ov = a
    sd = next(s for s in S if s.id == sid)
    return (sid, pol, g, simulate_cell(sd, P, POL[pol], G[g], T, runs, zlib.crc32(f"{sid}{pol}{g}{sorted(ov.items())}".encode()) % 2**31, ov))

ENEMY = [(1.5, 1.3), (2.0, 1.5)]
BOSS = [(1.0, 1.0, 1.0), (1.5, 0.67, 0.85), (1.6, 0.6, 0.75), (2.0, 0.6, 0.7)]
runs = int(sys.argv[1]) if len(sys.argv) > 1 else 300
print("| 적 HP×ATK | 보스 HP×ATK×속도 | D/G1 ★3 1-4~1-7 | D/G1 보스 ★3 / 클리어 | D/G0 보스 클리어 | S/G1 보스 ★3 | S/G1 ★3>20% (1-4~1-8) | A/G1 1-4~1-7 클리어 | D/G1 넉다운 합 | D/G1 군단 이탈 합 | D/G1 per stage ★3 |")
print("| :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :--- |")
with Pool(4) as pool:
    for (eh, ea), (bh, ba, bs) in itertools.product(ENEMY, BOSS):
        ov = {"enemy_hp_mult": eh, "enemy_atk_mult": ea, "boss_hp_mult": bh, "boss_atk_mult": ba, "boss_speed_mult": bs}
        jobs = [(s.id, pol, g, runs, ov) for s in S for pol, g in (("D", "G1"), ("S", "G1"), ("A", "G1"), ("D", "G0"))]
        R = {(sid, pol, g): m for sid, pol, g, m in pool.map(cell, jobs)}
        late = [R[(s, "D", "G1")]["P_star3"] for s in ("1-4", "1-5", "1-6", "1-7")]
        a_late = [R[(s, "A", "G1")]["P_clear"] for s in ("1-4", "1-5", "1-6", "1-7")]
        solo = sum(1 for s in ("1-4", "1-5", "1-6", "1-7", "1-8") if R[(s, "S", "G1")]["P_star3"] > 0.2)
        per = " ".join(f"{s.id}:{R[(s.id,'D','G1')]['P_star3']*100:.0f}" for s in S)
        print(f"| {eh}×{ea} | {bh}×{ba}×{bs} | {sum(late)/4*100:.0f}% | {R[('1-8','D','G1')]['P_star3']*100:.0f}% / {R[('1-8','D','G1')]['P_clear']*100:.0f}% | {R[('1-8','D','G0')]['P_clear']*100:.0f}% | {R[('1-8','S','G1')]['P_star3']*100:.0f}% | {solo}/5 | {sum(a_late)/4*100:.0f}% | {sum(R[(s.id,'D','G1')]['knockdowns'] for s in S):.2f} | {sum(R[(s.id,'D','G1')]['legion_deaths'] for s in S):.2f} | {per} |", flush=True)
