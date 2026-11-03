#!/usr/bin/env python3
"""밸런스 시트 생성 — 단일 원본(tools/difficulty_sim/params.yaml · unity/Data/Enemies.json · unity/Data/Stages)에서 docs/data/*.csv 를 만든다.
실행: python3 -I tools/export_balance_sheets.py"""
import csv, glob, json, os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "difficulty_sim"))
import yaml
from model import build_hero_stats, build_unit_stats, load_params, load_enemy_table, build_enemy_stats

ROOT = os.path.join(HERE, "..")
OUT = os.path.join(ROOT, "docs", "data")
P = load_params()
T = load_enemy_table(P)
os.makedirs(OUT, exist_ok=True)

def w(name, header, rows):
    with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8") as f:
        cw = csv.writer(f); cw.writerow(header); cw.writerows(rows)
    print(f"{name}: {len(rows)} rows")

# 1. 주인공 레벨 곡선 (스탯 미배분 / 챕터 권장 빌드)
H = P["hero"]; xp_rows = []; cum = 0
for L in range(1, 61):
    need = int(60 * L ** 1.4)
    base = build_hero_stats(P, "awakened", {"hero_level": L, "stats": {}, "tree": []}, {})
    xp_rows.append([L, need, cum, round(base["hp"]), round(base["atk"]), round(base["def"]), round(base["res"], 1), round(base["interval"], 3),
                    round(base["relocate_cd"], 2), 3 * (L - 1), (L // 5)])
    cum += need
w("hero_levels.csv", ["level", "xp_to_next", "xp_cumulative", "hp", "atk", "def", "res", "attack_interval", "relocate_cd", "stat_points", "skill_points_from_level"], xp_rows)

# 2. 챕터별 성장 상태의 주인공 실효치
rows = []
for ch, states in P["growth_by_chapter"].items():
    for gk, g in states.items():
        s = build_hero_stats(P, "awakened", g, {})
        rows.append([ch, gk, g["name"], g["hero_level"], json.dumps(g.get("stats", {}), ensure_ascii=False), "+".join(g.get("tree", [])), round(s["hp"]), round(s["atk"]), round(s["def"]),
                     round(s["res"], 1), round(s["interval"], 3), round(s["relocate_cd"], 2), s["block"], s["range_front"], round(s["cmd_dp"], 2), round(s["cmd_legion"], 3),
                     g["legion_level"], g["awaken"], g["skill_rank"]])
w("hero_growth_states.csv", ["chapter", "state", "name", "hero_level", "stat_alloc", "tree", "hp", "atk", "def", "res", "attack_interval", "relocate_cd", "block", "range_front", "cmd_dp_mult", "cmd_legion_bonus", "legion_level", "awaken", "skill_rank"], rows)

# 3. 클래스 템플릿 × 희귀도 × 각성 × 대표 레벨
rows = []
LG = P["legion"]
for cls, c in P["classes"].items():
    if cls == "civilian": continue
    for rar in (3, 4, 5, 6):
        for aw in (0, 1, 2):
            for L in (1, 15, 30, 50, 70):
                if L > LG["max_level"][aw]: continue
                if rar == 3 and aw == 2: continue
                mult = (1 + LG["level_growth"] * (L - 1)) * LG["awaken_mult"][aw] * LG["rarity_mult"][rar]
                rows.append([cls, rar, aw, L, round(c["hp"] * mult), round(c["atk"] * mult), round(c["def"] * mult), c["res"], c["block"],
                             max(1, c["cost"] + LG["rarity_cost_add"][rar]), c["redeploy"], c["interval"], c["range"] if not (aw >= 1 and c["range"] == "R3") else "R3p", c["dmg"], c.get("skill", {}).get("name", "")])
w("legion_templates.csv", ["class", "rarity", "awaken", "level", "hp", "atk", "def", "res", "block", "cost", "redeploy_s", "attack_interval", "range", "damage", "skill"], rows)

# 4. 로스터 24 (클래스 · 희귀도 · 합류)
units = {**P["units"]}
rows = [[uid, u["class"], u.get("rarity", 4), u.get("block", P["classes"][u["class"]]["block"]), u.get("fixed_level", "")] for uid, u in units.items() if u["class"] != "civilian"]
w("roster.csv", ["unit_id", "class", "rarity", "block", "fixed_level"], rows)

# 5. 적 × 챕터 (배율 적용 실효치)
scales = {1: {"hp": 1, "atk": 1, "def": 1}}
for p in glob.glob(os.path.join(ROOT, "unity", "Data", "Stages", "Stage_*.json")):
    d = json.load(open(p, encoding="utf-8")); scales.setdefault(d["chapter"], d["scale"])
rows = []
for eid, e in T.items():
    for ch in sorted(scales):
        st = build_enemy_stats(T, eid, scales[ch], {})
        rows.append([eid, e.get("name", ""), e["kind"], ch, round(st["hp"]), round(st["atk"]), round(st["def"]), st["res"], st["speed"], e.get("weight", ""), st["flying"], st["ranged"], st["arts"],
                     e.get("interval", 1.0), e.get("ability", ""), e.get("first", e.get("stage", ""))])
w("enemies_by_chapter.csv", ["enemy_id", "name", "kind", "chapter", "hp", "atk", "def", "res", "speed", "weight", "flying", "ranged_tiles", "arts", "attack_interval", "ability", "first_stage"], rows)

# 6. 스테이지 경제 (초기 DP · 회복 · 배치 제한 · 적 수 · 기본 편성 코스트 합 · 길이)
rows = []
for p in sorted(glob.glob(os.path.join(ROOT, "unity", "Data", "Stages", "Stage_*.json")), key=lambda q: (os.path.basename(q)[6:-5].startswith("SC"), [v.zfill(4) for v in os.path.basename(q)[6:-5].split("-")])):
    d = json.load(open(p, encoding="utf-8")); sq = P["squads"].get(d["id"], {})
    g1 = P["growth_by_chapter"][d["chapter"]]["G1"]
    costs = [build_unit_stats(P, uid, g1, 0.0, {})["cost"] for uid in sq.get("legion", [])]
    last = max(wv["t"] + max(wv["count"] - 1, 0) * wv.get("interval", 0) for wv in d["waves"])
    natural = d["initial_dp"] + d["dp_regen"] * last
    rows.append([d["id"], d["chapter"], d["name"], d["lives"], d["initial_dp"], d["dp_regen"], d["deploy_limit"], len(d["routes"]), len(d.get("routes_air", {})), d["enemy_total"],
                 round(last), len(costs), sum(costs), round(natural), (d.get("boss") or {}).get("id", ""), d["scale"]["hp"], d["scale"]["atk"]])
w("stages.csv", ["stage", "chapter", "name", "lives", "initial_dp", "dp_regen", "deploy_limit", "routes", "routes_air", "enemy_total", "last_spawn_s", "cards_g1", "squad_cost_sum", "natural_dp_by_last_spawn", "boss", "scale_hp", "scale_atk"], rows)

# 7. 보스
rows = [[b["id"], b["name"], b["hp"], b["atk"], b["def"], b["res"], b["speed"], b.get("interval", 1.0), ",".join(b.get("abilities", [])), b.get("stage", "")] for b in json.load(open(os.path.join(ROOT, "unity", "Data", "Enemies.json"), encoding="utf-8"))["bosses"]]
w("bosses.csv", ["boss_id", "name", "hp", "atk", "def", "res", "speed", "attack_interval", "abilities", "stage"], rows)

# 8. 규칙 상수 (params → 평탄화)
rows = []
def flat(prefix, obj):
    if isinstance(obj, dict):
        for k, v in obj.items(): flat(f"{prefix}.{k}" if prefix else k, v)
    elif isinstance(obj, list):
        rows.append([prefix, json.dumps(obj, ensure_ascii=False)])
    else:
        rows.append([prefix, obj])
for key in ("rules", "hero", "legion", "sim"):
    flat(key, P[key])
w("rules.csv", ["key", "value"], rows)
