#!/usr/bin/env python3
"""StageDef 검증기: unity/Data/Stages/*.json 을 읽어 격자 · 경로 · 웨이브 · 적 ID · NPC 타일을 검사한다. 실패가 있으면 종료 코드 1."""
import json, glob, os, sys

ROOT = os.path.join(os.path.dirname(__file__), "..", "unity", "Data")
WALK = set("GPSDLTAR")      # 적이 지나갈 수 있는 타일
GROUND = set("GLTAR")       # 지상 소집 가능 (L 은 군단원만)
HERO_OK = set("GTAR")       # 주인공이 설 수 있는 타일

def load_enemies():
    e = json.load(open(os.path.join(ROOT, "Enemies.json"), encoding="utf-8"))
    ids = {b["id"] for b in e["bases"]} | {v["id"] for v in e["variants"]} | {b["id"] for b in e["bosses"]}
    return ids

def tile(grid, x, y):
    rows = grid["rows"]; h = grid["h"]
    return rows[h - 1 - y][x]

def check(path, enemy_ids):
    errs = []
    s = json.load(open(path, encoding="utf-8"))
    g = s["grid"]; w, h = g["w"], g["h"]
    if len(g["rows"]) != h or any(len(r) != w for r in g["rows"]):
        errs.append("grid size mismatch"); return errs
    # routes
    for rid, pts in s["routes"].items():
        if tile(g, *pts[0]) != "S": errs.append(f"route {rid}: start {pts[0]} is not S")
        if tile(g, *pts[-1]) != "D": errs.append(f"route {rid}: end {pts[-1]} is not D")
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            if x0 != x1 and y0 != y1: errs.append(f"route {rid}: diagonal segment {(x0,y0)}->{(x1,y1)}"); continue
            xs = range(min(x0, x1), max(x0, x1) + 1); ys = range(min(y0, y1), max(y0, y1) + 1)
            for x in xs:
                for y in ys:
                    if tile(g, x, y) not in WALK: errs.append(f"route {rid}: tile {(x,y)}={tile(g,x,y)} not walkable")
    for rid, pts in s.get("routes_air", {}).items():
        for x, y in pts:
            if not (0 <= x < w and 0 <= y < h): errs.append(f"air route {rid}: {(x,y)} outside")
    # waves
    total = 0
    for i, wv in enumerate(s["waves"]):
        if wv["enemy"] not in enemy_ids: errs.append(f"wave {i}: unknown enemy {wv['enemy']}")
        if wv["route"] not in s["routes"] and wv["route"] not in s.get("routes_air", {}): errs.append(f"wave {i}: unknown route {wv['route']}")
        if wv["count"] < 1: errs.append(f"wave {i}: count < 1")
        total += wv["count"]
    if total != s["enemy_total"]: errs.append(f"enemy_total {s['enemy_total']} != sum(waves) {total}")
    # hero
    ht = s["hero"]["default_tile"]
    if ht is not None and tile(g, *ht) not in HERO_OK: errs.append(f"hero default tile {ht}={tile(g,*ht)} not allowed")
    for st in s.get("sealed_tiles", []):
        if tile(g, *st) != "L": errs.append(f"sealed tile {st} is not L in grid")
    if s.get("boss"):
        for ph in s["boss"]["phases"]:
            for st in ph["sealed"]:
                if tile(g, *st) not in WALK: errs.append(f"boss phase sealed {st} not walkable")
    # npc
    for n in s.get("npc_units", []):
        t = tile(g, *n["tile"])
        if t not in GROUND | {"H"}: errs.append(f"npc {n['id']} tile {n['tile']}={t} not deployable")
    # deploy limit vs ground tiles
    ground = sum(r.count("G") + r.count("L") + r.count("T") + r.count("A") + r.count("R") for r in g["rows"])
    high = sum(r.count("H") for r in g["rows"])
    if s["deploy_limit"] > ground + high: errs.append("deploy_limit exceeds deployable tiles")
    stats = f"{s['id']} {s['name']}: enemies {total}, routes {len(s['routes'])}+air {len(s.get('routes_air', {}))}, ground {ground}, high {high} ({high/(ground+high):.0%})"
    return errs, stats

def main():
    ids = load_enemies()
    bad = 0
    for p in sorted(glob.glob(os.path.join(ROOT, "Stages", "*.json")), key=lambda q: (os.path.basename(q)[6:-5].startswith("SC"), [v.zfill(4) for v in os.path.basename(q)[6:-5].split("-")])):
        errs, stats = check(p, ids)
        print(("FAIL " if errs else "ok   ") + stats)
        for e in errs: print("     -", e)
        bad += bool(errs)
    sys.exit(1 if bad else 0)

if __name__ == "__main__":
    main()
