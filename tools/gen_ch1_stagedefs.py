#!/usr/bin/env python3
"""1장(각성) 8스테이지 StageDef 생성기. 이 파일이 원본이고 unity/Data/Stages/Stage_1-*.json 은 출력물이다.

좌표 규약: x = 열(0..w-1, 왼쪽부터), y = 행(0..h-1, 아래부터). grid.rows 는 위(y=h-1)부터 아래(y=0) 순서.
타일 코드(02 GDD §3.1): G 지상 · H 고지대 · X 배치 불가 · P 통로(배치 불가, 통행 가능) · S 출현 · D 방어 · L 봉인 · T 함정 · A 가속 · R 치유
"""
import json, os, sys

OUT = os.path.join(os.path.dirname(__file__), "..", "unity", "Data", "Stages")

def stage(id_, name, rows, routes, waves, *, lives=5, initial_dp=10, dp_regen=0.7, deploy_limit=6,
          hero=None, hero_mode="awakened", sealed=None, npc=None, dispatch=None, script=None,
          rewards=None, first_clear=None, unlock=None, challenge=None, seed=None, boss=None, note=""):
    assert len(rows) == 8 and all(len(r) == 13 for r in rows), id_
    total = sum(w["count"] for w in waves)
    return {
        "id": id_, "chapter": 1, "type": "main", "name": name, "note": note,
        "grid": {"w": 13, "h": 8, "rows": rows},
        "lives": lives, "initial_dp": initial_dp, "dp_regen": dp_regen, "deploy_limit": deploy_limit,
        "hero": {"mode": hero_mode, "default_tile": hero},
        "sealed_tiles": sealed or [],
        "routes": routes,
        "waves": waves,
        "enemy_total": total,
        "scale": {"hp": 1.0, "atk": 1.0, "def": 1.0},
        "npc_units": npc or [],
        "dispatch_units": dispatch or [],
        "boss": boss,
        "script": script or [],
        "rewards": rewards or {"xp": 300, "gold": 200, "drops": []},
        "first_clear": first_clear or {"gem": 10},
        "unlock_scenario": unlock,
        "challenge": challenge or {"mods": ["deploy_limit-1", "enemy_hp+30"]},
        "seed": seed if seed is not None else 1000 + int(id_.split("-")[1]),
    }

def W(t, enemy, route, count, interval=2.0):
    return {"t": t, "enemy": enemy, "route": route, "count": count, "interval": interval}

STAGES = []

# ---------- 1-1 짐꾼: 소집 · 방향 · 저지 ----------
rows_11 = [
    "XXXXXXXXXXXXX",
    "XXXHHHXHHHXXX",
    "XXGGGGGGGGGXX",
    "XGGGGGGGGGGGX",
    "SPGGGGGGGGGPD",
    "XGGGGGGGGGGGX",
    "XXGGGGGGGGGXX",
    "XXXXXXXXXXXXX",
]
STAGES.append(stage("1-1", "짐꾼", rows_11,
    {"A": [[0, 3], [12, 3]]},
    [W(3, "E01", "A", 4, 2.5), W(22, "E01", "A", 4, 2.5)],
    lives=10, deploy_limit=3, hero=[7, 3], hero_mode="pre_awakening",
    npc=[{"id": "NPC_MUJIN", "unit": "L_SHIELD_MUJIN", "tile": [5, 3], "dir": "W", "level": 10}],
    dispatch=["DSP_SPEAR", "DSP_SNIPER"],
    script=[{"t": 0, "event": "tutorial", "key": "deploy_drag_direction"},
            {"t": 20, "event": "tutorial", "key": "block_and_highground"}],
    rewards={"xp": 300, "gold": 150, "drops": []},
    challenge=None, note="각성 전. 무진 NPC가 길목을 막고, 파견 창병 · 사수로 소집 · 방향 · 고지대를 배운다."))

# ---------- 1-2 오판: 귀환 · 재소집 · 자동 스킬 ----------
STAGES.append(stage("1-2", "오판", rows_11,
    {"A": [[0, 3], [12, 3]]},
    [W(3, "E01", "A", 4, 2.0), W(18, "E01", "A", 4, 2.0), W(34, "E01", "A", 4, 1.5), W(52, "E01_elite", "A", 1, 0)],
    lives=10, deploy_limit=3, hero=[7, 3], hero_mode="pre_awakening",
    npc=[{"id": "NPC_MUJIN", "unit": "L_SHIELD_MUJIN", "tile": [5, 3], "dir": "W", "level": 10},
         {"id": "NPC_DOKYUNG", "unit": "L_SPEAR_DOKYUNG", "tile": [8, 3], "dir": "W", "level": 8}],
    dispatch=["DSP_SPEAR", "DSP_SNIPER"],
    script=[{"t": 0, "event": "tutorial", "key": "auto_skill"},
            {"t": 30, "event": "npc_down", "unit": "NPC_DOKYUNG"},
            {"t": 31, "event": "tutorial", "key": "retreat_and_resummon"},
            {"t": 50, "event": "cutscene", "key": "ch1_elite_appears"}],
    rewards={"xp": 350, "gold": 150, "drops": []},
    challenge=None, note="C급 판정이 오판. 도경이 쓰러지고(30s) 엘리트가 나타난다. 귀환 · 재소집을 가르친다."))

# ---------- 1-3 낙인: 각성 · 재배치 · 기세 (솔로) ----------
rows_13 = [
    "XXXXXXXXXXXXX",
    "XXXXHHHXXXXXX",
    "SGGGGGGGGGGPD",
    "XXGGXXXXXXGGX",
    "XXGGXHHHXXGGX",
    "XXGGXXXXXXGGX",
    "SGGGGGGGGGGPD",
    "XXXXXXXXXXXXX",
]
STAGES.append(stage("1-3", "낙인", rows_13,
    {"A": [[0, 5], [12, 5]], "B": [[0, 1], [12, 1]]},
    [W(3, "E01", "A", 5, 2.0), W(28, "E01", "B", 5, 2.0), W(52, "E02", "A", 3, 3.0),
     W(70, "E01", "B", 3, 2.0), W(78, "E02", "B", 2, 3.0)],
    lives=5, deploy_limit=0, hero=[9, 5], hero_mode="awakened",
    script=[{"t": 0, "event": "cutscene", "key": "ch1_awakening"},
            {"t": 0, "event": "system_window", "key": "brand_first_contact"},
            {"t": 24, "event": "tutorial", "key": "hero_relocate"},
            {"t": 50, "event": "tutorial", "key": "momentum_and_ranged_enemy"}],
    rewards={"xp": 500, "gold": 200, "drops": []},
    first_clear={"gem": 20, "scenario": "SC-01"},
    challenge=None, note="주인공 단독. 두 방어 지점을 재배치로 오가며 막는다. 궁수(E02) 첫 등장. 클리어 후 SC-01 첫 낙인(도경)."))

# ---------- 1-4 하수도 교차로: 수동 스킬 · 경로 2 (R1) · 민간인 ----------
rows_14 = [
    "XXXXXXXXXXXXX",
    "SGGGGGGGGGGGX",
    "XXHHXXXXXHHGX",
    "XXXXXXXXXXXGX",
    "XXHHXXXXXXXGD",
    "XXXXXXXXXXXGX",
    "XXHHXXXXXHHGX",
    "SGGGGGGGGGGGX",
]
STAGES.append(stage("1-4", "하수도 교차로", rows_14,
    {"A": [[0, 6], [11, 6], [11, 3], [12, 3]], "B": [[0, 0], [11, 0], [11, 3], [12, 3]]},
    [W(3, "E01", "A", 4, 2.0), W(15, "E01", "B", 4, 2.0), W(35, "E01", "A", 5, 1.8), W(42, "E02", "A", 1, 0),
     W(50, "E01", "B", 4, 1.8), W(57, "E02", "B", 1, 0), W(75, "E01_elite", "A", 1, 0), W(76, "E01", "B", 3, 1.5)],
    lives=5, deploy_limit=4, hero=[8, 6],
    npc=[{"id": "CIV_01", "unit": "CIVILIAN", "tile": [5, 0], "dir": "E", "level": 1, "role": "survivor"}],
    dispatch=["DSP_SPEAR", "DSP_SNIPER"],
    script=[{"t": 0, "event": "tutorial", "key": "manual_skill"},
            {"t": 12, "event": "tutorial", "key": "two_routes_hero_cannot_hold_both"}],
    rewards={"xp": 450, "gold": 250, "drops": [["T1_core", 0.5]]},
    unlock={"id": "SC-H01", "condition": "npc_alive:CIV_01", "unit": "L_SUPPORT_JOY", "hint": "생존자를 끝까지 지킬 것"},
    note="R1 첫 적용. 생존자(민간인) NPC가 B 경로 위에 있다. 끝까지 살리면 숨은 합류 H01(조이)."))

# ---------- 1-5 방패: 고지대 · 사수 · 돌진병, 분기 경로 ----------
rows_15 = [
    "XXXXXXXXXXXXX",
    "XXGGGGGGGGGPD",
    "XXPXHHHHHXXXX",
    "SPPXHXXXHXXXX",
    "XXPXHHHHHXXXX",
    "XXGGGGGGGGGPD",
    "XXXXXXXXXXXXX",
    "XXXXXXXXXXXXX",
]
STAGES.append(stage("1-5", "방패", rows_15,
    {"A": [[0, 4], [2, 4], [2, 6], [12, 6]], "B": [[0, 4], [2, 4], [2, 2], [12, 2]]},
    [W(3, "E01", "A", 4, 2.0), W(12, "E01", "B", 4, 2.0), W(30, "E03", "A", 2, 3.0), W(40, "E01", "B", 5, 1.8),
     W(60, "E01", "A", 4, 1.8), W(67, "E03", "A", 1, 0), W(75, "E03", "B", 2, 3.0)],
    lives=5, deploy_limit=5, hero=[4, 6],
    npc=[{"id": "NPC_MUJIN", "unit": "L_SHIELD_MUJIN", "tile": [4, 2], "dir": "W", "level": 12, "role": "companion"}],
    dispatch=["DSP_SPEAR", "DSP_SNIPER"],
    script=[{"t": 0, "event": "tutorial", "key": "sniper_on_highground_covers_both_lanes"},
            {"t": 28, "event": "tutorial", "key": "charger_enemy_first_hit_x2"}],
    rewards={"xp": 500, "gold": 250, "drops": [["T1_core", 0.5]]},
    first_clear={"gem": 10, "scenario": "SC-02"},
    note="출현 지점 하나가 통로(P)에서 두 갈래로 갈라진다. 주인공은 한쪽만 막을 수 있다. 무진이 아래 길을 지킨다. 클리어 후 SC-02 방패(무진)."))

# ---------- 1-6 깊은 곳: 권능 일섬 · 엘리트 · 숨은 합류 H02 ----------
rows_16 = [
    "XXXXXXXXXXXXX",
    "SGGGGGGGGGGGX",
    "XHHXXXXXXXHPX",
    "XXXXXXXXXXXPD",
    "XHHXXXXXXXHPX",
    "SGGGGGGGGGGGX",
    "XXXXXXXXXXXXX",
    "XXXXXXXXXXXXX",
]
STAGES.append(stage("1-6", "깊은 곳", rows_16,
    {"A": [[0, 6], [11, 6], [11, 4], [12, 4]], "B": [[0, 2], [11, 2], [11, 4], [12, 4]]},
    [W(3, "E01", "A", 5, 2.0), W(10, "E01", "B", 5, 2.0), W(30, "E01_elite", "A", 1, 0), W(31, "E02", "A", 2, 3.0),
     W(40, "E03", "B", 2, 3.0), W(60, "E03_elite", "A", 1, 0), W(62, "E01", "B", 5, 1.5), W(70, "E02", "B", 2, 3.0),
     W(90, "E01_elite", "A", 1, 0), W(90, "E01_elite", "B", 1, 0)],
    lives=5, deploy_limit=5, hero=[6, 6],
    dispatch=["DSP_SPEAR", "DSP_SNIPER"],
    script=[{"t": 0, "event": "unlock", "key": "ult_flash_slash"},
            {"t": 0, "event": "tutorial", "key": "ult_sp_from_all_kills"},
            {"t": 58, "event": "cutscene", "key": "ch1_predator_appears"}],
    rewards={"xp": 550, "gold": 300, "drops": [["T1_core", 0.6], ["T1_shard", 0.3]]},
    unlock={"id": "SC-H02", "condition": "hero_kill:E03_elite", "unit": "L_SPEAR_GROL", "hint": "하수도의 포식자를 직접 쓰러뜨릴 것"},
    note="방어 지점 앞 3칸이 통로(P)라 마지막 합류 지점에 설 수 없다. 권능 일섬 해금. 포식자(E03 엘리트)를 주인공이 직접 처치하면 H02(그롤)."))

# ---------- 1-7 예속: 교차 경로 · 정찰병 · 숨은 합류 안내 ----------
rows_17 = [
    "XXXXXXXXXXXXX",
    "SGGGGGGGGGGPD",
    "XGXXHHHHHXXGX",
    "XGGGGGGGGGGGX",
    "XGXXHHHHHXXGX",
    "SGGGGGGGGGGPD",
    "XXXXXXXXXXXXX",
    "XXXXXXXXXXXXX",
]
STAGES.append(stage("1-7", "예속", rows_17,
    {"A": [[0, 6], [12, 6]], "B": [[0, 2], [12, 2]], "C": [[0, 6], [1, 6], [1, 4], [11, 4], [11, 2], [12, 2]]},
    [W(3, "E01", "A", 4, 2.0), W(8, "E01", "B", 4, 2.0), W(25, "E02", "C", 3, 3.0), W(35, "E01", "A", 3, 2.0),
     W(38, "E02", "A", 2, 3.0), W(45, "E01_scout", "B", 1, 0), W(47, "E01", "B", 3, 2.0), W(65, "E01_elite", "C", 1, 0),
     W(66, "E02", "C", 2, 3.0), W(80, "E02", "A", 3, 2.5), W(82, "E01", "B", 4, 1.5)],
    lives=5, deploy_limit=6, hero=[6, 6],
    dispatch=["DSP_SPEAR", "DSP_SNIPER"],
    script=[{"t": 0, "event": "tutorial", "key": "crossing_route"},
            {"t": 44, "event": "cutscene", "key": "ch1_scout_kick"},
            {"t": -1, "event": "system_window", "key": "hidden_join_hint_reveal"}],
    rewards={"xp": 600, "gold": 300, "drops": [["T1_core", 0.6], ["T1_shard", 0.4]]},
    first_clear={"gem": 10, "scenario": "SC-03"},
    note="C 경로가 위에서 시작해 아래 방어 지점으로 건너간다. 정찰병 킥(빠른 적)이 등장하고 클리어 후 SC-03 예속(킥). 결과 창에서 1-4 · 1-6의 숨은 조건을 공개한다."))

# ---------- 1-8 하수도 군주: 보스 · 페이즈 · 봉인 타일 ----------
rows_18 = [
    "XXXXXXXXXXXXX",
    "XXHHXXXXXXXXX",
    "XGGGGGGGGGGGX",
    "SPGGLLLLLGGPD",
    "XGGGGGGGGGGGX",
    "XXHHXXXXXHHXX",
    "XXXXXXXXXXXXX",
    "XXXXXXXXXXXXX",
]
boss_18 = {
    "id": "B01", "name": "하수도 군주", "route": "A", "spawn_t": 20,
    "phases": [
        {"hp_above": 0.5, "sealed": [[4, 4], [5, 4], [6, 4], [7, 4], [8, 4]], "summon_every": 15, "summon": ["E01", 2]},
        {"hp_above": 0.0, "sealed": [[3, 4], [4, 4], [5, 4], [6, 4], [7, 4], [8, 4], [9, 4]], "summon_every": 10, "summon": ["E01", 2],
         "on_enter": ["invuln_2s", "roar_push_1"]},
    ],
}
STAGES.append(stage("1-8", "하수도 군주", rows_18,
    {"A": [[0, 4], [12, 4]]},
    [W(3, "E01", "A", 4, 2.0), W(20, "B01", "A", 1, 0),
     W(35, "E01", "A", 2, 1.0), W(50, "E01", "A", 2, 1.0), W(65, "E01", "A", 2, 1.0),
     W(80, "E01", "A", 2, 1.0), W(95, "E01", "A", 2, 1.0), W(110, "E01", "A", 2, 1.0)],
    lives=3, initial_dp=15, deploy_limit=6, hero=[2, 4],
    sealed=[[4, 4], [5, 4], [6, 4], [7, 4], [8, 4]],
    dispatch=["DSP_SPEAR", "DSP_SNIPER"],
    boss=boss_18,
    script=[{"t": 0, "event": "cutscene", "key": "ch1_boss_intro"},
            {"t": 20, "event": "tutorial", "key": "boss_sealed_tiles_hero_cannot_enter"},
            {"t": -1, "event": "cutscene", "key": "ch1_boss_clear_rank_up_D"}],
    rewards={"xp": 900, "gold": 500, "drops": [["T1_core", 1.0], ["T2_core", 0.3]]},
    first_clear={"gem": 30, "skill_point": 1, "rank": "D", "level_cap": 25},
    challenge={"mods": ["deploy_limit-2", "dp_regen-30"]},
    note="보스가 느리게 전진하며 15s마다 고블린을 소환한다. 봉인 타일(중앙 5칸)에는 주인공이 설 수 없어 군단이 중앙을 맡는다. 50% 페이즈 전환 시 봉인이 양쪽 1칸씩 넓어진다. 보스가 방어 지점에 닿으면 즉시 실패."))

def main():
    os.makedirs(OUT, exist_ok=True)
    index = []
    for s in STAGES:
        path = os.path.join(OUT, f"Stage_{s['id']}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, indent=2)
        index.append({"id": s["id"], "name": s["name"], "file": os.path.basename(path), "enemy_total": s["enemy_total"],
                      "lives": s["lives"], "deploy_limit": s["deploy_limit"], "routes": len(s["routes"])})
    with open(os.path.join(OUT, "..", "StageIndex.json"), "w", encoding="utf-8") as f:
        json.dump({"chapter": 1, "stages": index}, f, ensure_ascii=False, indent=2)
    print(f"wrote {len(STAGES)} stages to {os.path.normpath(OUT)}")

if __name__ == "__main__":
    main()
