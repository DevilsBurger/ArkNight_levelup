"""results.csv → 마크다운 표. 예) python3 -I report.py out/results.csv"""
from __future__ import annotations
import csv, sys
from collections import defaultdict
from pathlib import Path


def load(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def pct(x):
    return f"{float(x) * 100:.0f}%"


def table_by_policy(rows, growth, metric="P_star3", tag="base"):
    pols = sorted({r["policy"] for r in rows if r["growth"] == growth and r["tag"] == tag}, key=lambda p: "SABCDE".index(p) if p in "SABCDE" else 9)
    stages = sorted({r["stage"] for r in rows}, key=lambda s: tuple(int(v) for v in s.split("-")))
    idx = {(r["stage"], r["policy"]): r for r in rows if r["growth"] == growth and r["tag"] == tag}
    out = ["| 스테이지 | " + " | ".join(pols) + " |", "| :-: | " + " | ".join(":-:" for _ in pols) + " |"]
    for s in stages:
        out.append(f"| {s} | " + " | ".join(pct(idx[(s, p)][metric]) if (s, p) in idx else "—" for p in pols) + " |")
    return "\n".join(out)


def table_by_growth(rows, policy, metric="P_star3", tag="base"):
    gs = sorted({r["growth"] for r in rows if r["policy"] == policy and r["tag"] == tag})
    stages = sorted({r["stage"] for r in rows}, key=lambda s: tuple(int(v) for v in s.split("-")))
    idx = {(r["stage"], r["growth"]): r for r in rows if r["policy"] == policy and r["tag"] == tag}
    out = ["| 스테이지 | " + " | ".join(gs) + " |", "| :-: | " + " | ".join(":-:" for _ in gs) + " |"]
    for s in stages:
        out.append(f"| {s} | " + " | ".join(pct(idx[(s, g)][metric]) if (s, g) in idx else "—" for g in gs) + " |")
    return "\n".join(out)


def table_detail(rows, policy, growth, tag="base"):
    stages = sorted({r["stage"] for r in rows}, key=lambda s: tuple(int(v) for v in s.split("-")))
    idx = {r["stage"]: r for r in rows if r["policy"] == policy and r["growth"] == growth and r["tag"] == tag}
    out = ["| 스테이지 | P_clear | P_★3 | 누수 | 넉다운 | 군단 이탈 | 재배치 | 권능 | 주인공 처치 비율 | DP 소비 | 처치 DP | 소집 | T(s) |",
           "| :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |"]
    for s in stages:
        r = idx.get(s)
        if not r: continue
        out.append(f"| {s} | {pct(r['P_clear'])} | {pct(r['P_star3'])} | {float(r['leaks']):.2f} | {float(r['knockdowns']):.2f} | {float(r['legion_deaths']):.2f} | "
                   f"{float(r['relocates']):.1f} | {float(r['ult_uses']):.1f} | {pct(r['hero_kill_share'])} | {float(r['dp_spent']):.0f} | {float(r['dp_kill']):.0f} | {float(r['deploys']):.1f} | {float(r['T_mean']):.0f} |")
    return "\n".join(out)


def table_tags(rows, policy, growth, metric="P_star3"):
    tags = sorted({r["tag"] for r in rows if r["policy"] == policy and r["growth"] == growth}, key=lambda t: (t != "base", t))
    stages = sorted({r["stage"] for r in rows}, key=lambda s: tuple(int(v) for v in s.split("-")))
    idx = {(r["stage"], r["tag"]): r for r in rows if r["policy"] == policy and r["growth"] == growth}
    out = ["| 스테이지 | " + " | ".join(tags) + " |", "| :-: | " + " | ".join(":-:" for _ in tags) + " |"]
    for s in stages:
        out.append(f"| {s} | " + " | ".join(pct(idx[(s, t)][metric]) if (s, t) in idx else "—" for t in tags) + " |")
    return "\n".join(out)


if __name__ == "__main__":
    rows = load(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent / "out" / "results.csv")
    print("## P_★3 by policy (G1)\n" + table_by_policy(rows, "G1"))
    print("\n## P_clear by policy (G1)\n" + table_by_policy(rows, "G1", "P_clear"))
    print("\n## P_★3 by growth (D)\n" + table_by_growth(rows, "D"))
    print("\n## detail D/G1\n" + table_detail(rows, "D", "G1"))
