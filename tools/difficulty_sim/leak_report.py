"""저조 스테이지의 누수를 레인 · 시간대 · 적 종류별로 집계 (D·G1). 예) python3 -I leak_report.py 2-4,2-7 100"""
import sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from stagedef_loader import load_stages
from model import load_params, load_policies, load_enemy_table, Sim
P = load_params(); POL = load_policies(); T = load_enemy_table(P)
ids = sys.argv[1].split(","); runs = int(sys.argv[2]) if len(sys.argv) > 2 else 100
S = {s.id: s for s in load_stages()}
for sid in ids:
    sd = S[sid]; growth = P["growth_by_chapter"][sd.chapter]["G1"]
    lanes = Counter(); win = Counter(); kinds = Counter(); fails = Counter(); deaths = Counter(); n_star3 = 0; n_clear = 0; econ = 0; kd = 0
    for i in range(runs):
        sim = Sim(sd, P, POL["D"], growth, T, 100 + i); m = sim.run()
        n_star3 += m["star3"]; n_clear += m["cleared"]; econ += sim.economy_moves; kd += m["knockdowns"]
        fails[m["fail"] or "ok"] += 1
        for t, lane, eid in sim.leak_log:
            lanes[lane] += 1; win[f"{int(t // 30) * 30:>3}-{int(t // 30) * 30 + 30}s"] += 1; kinds[eid] += 1
        for u in list(sim.units):
            pass
        deaths[m["legion_deaths"]] += 1
    print(f"\n### {sid} {sd.name} — D·G1 ★3 {n_star3/runs*100:.0f}% · 클리어 {n_clear/runs*100:.0f}% · 실패 {dict(fails)} · 경제 이동 {econ/runs:.1f}/런 · 넉다운 {kd/runs:.2f}")
    print("  레인별 누수/런:", {k: round(v / runs, 2) for k, v in sorted(lanes.items())})
    print("  시간대별:", {k: round(v / runs, 2) for k, v in sorted(win.items())})
    print("  적 종류:", {k: round(v / runs, 2) for k, v in kinds.most_common(6)})
