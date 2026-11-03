#!/usr/bin/env python3
"""2~5장 메인 32스테이지 StageDef 생성기 (04 문서 §6.2~6.5). 이 파일이 원본, unity/Data/Stages/Stage_{2..5}-*.json 은 출력물.
좌표 · 타일 코드 규약은 gen_ch1_stagedefs.py 와 같다. 보스 수치는 Enemies.json 의 최종값(챕터 배율 미적용)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from gen_ch1_stagedefs import stage, W, OUT

SCALE = {2: {"hp": 1.15, "atk": 1.12, "def": 1.09}, 3: {"hp": 1.33, "atk": 1.27, "def": 1.18},
         4: {"hp": 1.54, "atk": 1.45, "def": 1.27}, 5: {"hp": 1.84, "atk": 1.66, "def": 1.39}}   # GDD §7.5 초기값의 초과분 ×0.6 (08 §8 보정)
XP = {2: 1.25, 3: 1.55, 4: 1.9, 5: 2.4}

def meta(ch, idx, *, xp_factor=1.0, gem=10, boss=False):
    r = {"xp": int(300 * XP[ch] * (1.0 + 0.12 * (idx - 1)) * xp_factor), "gold": int(200 * XP[ch] * (1 + 0.1 * idx)),
         "drops": [[f"T{min(4, ch)}_core", 0.5]]}
    fc = {"gem": 30 if boss else gem}
    return r, fc

def npc(id_, unit, tile, d="E", level=15, role="companion"):
    return {"id": id_, "unit": unit, "tile": list(tile), "dir": d, "level": level, "role": role}

S = []
INIT_DP = {2: 12, 3: 15, 4: 18, 5: 20}      # 카드 수가 늘어나는 만큼 초기 DP 상향 (08 §8)
REGEN = {2: 0.7, 3: 0.75, 4: 0.8, 5: 0.85}

def space_opening(waves, air_routes, gap=8.0, air_min_t=20.0):
    """개막(t ≤ 15) 웨이브를 gap 간격으로 벌리고, 비행 경로 웨이브는 air_min_t 이후로 민다."""
    ws = sorted(waves, key=lambda w: w["t"])
    t_next = None
    for w in ws:
        if w["route"] in air_routes and w["t"] < air_min_t: w["t"] = air_min_t + (w["t"] - 3.0) * 2.0
    opening = [w for w in ws if w["t"] <= 15 and w["route"] not in air_routes]
    for k, w in enumerate(opening):
        w["t"] = 3.0 + gap * k
    return sorted(ws, key=lambda w: w["t"])

def add(ch, idx, name, rows, routes, waves, **kw):
    r, fc = meta(ch, idx, boss=kw.get("boss") is not None)
    kw.setdefault("rewards", r); kw.setdefault("first_clear", fc); kw.setdefault("scale", SCALE[ch])
    kw.setdefault("challenge", {"mods": ["deploy_limit-1", "enemy_hp+30"]})
    n_ground = len(routes)
    kw["initial_dp"] = max(kw.get("initial_dp", 0), INIT_DP[ch] + (3 if kw.get("boss") else 0) + (3 if n_ground >= 3 else 0))
    kw.setdefault("dp_regen", REGEN[ch])
    waves = space_opening([dict(w) for w in waves], set((kw.get("routes_air") or {}).keys()), gap=12.0 if n_ground >= 3 else 8.0)
    S.append(stage(f"{ch}-{idx}", name, rows, routes, waves, chapter=ch, **kw))

# ======================================================================= 2장 첫 군단 — 지하 미궁
T2a = ["XXXXXXXXXXXXX", "SGGGGGGGGGGPD", "XXHHXXXXXHHXX", "XXXXXXXXXXXXX", "XXHHXXXXXHHXX", "SGGGGGGGGGGPD", "XXXXXXXXXXXXX", "XXXXXXXXXXXXX"]
R2a = {"A": [[0, 6], [12, 6]], "B": [[0, 2], [12, 2]]}
T2b = ["XXXXXXXXXXXXX", "XXGGGGGGGGGPD", "XXPXHHHHHXXXX", "SPPXHXXXHXXXX", "XXPXHHHHHXGXX", "XXGGGGGGGGGGX", "XXXXXXXXXXGPD", "XXXXXXXXXXXXX"]
R2b = {"A": [[0, 4], [2, 4], [2, 6], [12, 6]], "B": [[0, 4], [2, 4], [2, 2], [10, 2], [10, 1], [12, 1]]}
T2c = ["XXXXXXXXXXXXX", "SGGGGGGGGGGPD", "XGXXHHHHHXXXX", "SGGGGGGGGGGPD", "XGXXHHHHHXXXX", "SGGGGGGGGGGPD", "XXXXXXXXXXXXX", "XXXXXXXXXXXXX"]
R2c = {"A": [[0, 6], [12, 6]], "B": [[0, 4], [12, 4]], "C": [[0, 2], [12, 2]]}
T2c2 = ["XXXXXXXXXXXXX", "SGGGGGGGGGGPD", "XGXXHHHHHXXXX", "SGGGGGGGGGGPX", "XGXXHHHHHXXPX", "SGGGGGGGGGGPD", "XXXXXXXXXXXXX", "XXXXXXXXXXXXX"]
R2c2 = {"A": [[0, 6], [12, 6]], "B": [[0, 4], [11, 4], [11, 2], [12, 2]], "C": [[0, 2], [12, 2]]}
T2d = ["XXXXXXXXXXXXX", "XXHHXXXXXHHXX", "SGGGGGGGGGGPD", "XXXXXXXXXXXXX", "SGGGGGGGGGGPD", "XXHHXXXXXHHXX", "XXXXXXXXXXXXX", "XXXXXXXXXXXXX"]
R2d = {"A": [[0, 5], [12, 5]], "B": [[0, 3], [12, 3]]}
TB = ["XXXXXXXXXXXXX", "XXHHXXXXXHHXX", "XGGGGGGGGGGGX", "SPGGLLLLLGGPD", "XGGGGGGGGGGGX", "SGGGGGGGGGGGX", "XXHHXXXXXHHXX", "XXXXXXXXXXXXX"]
RB = {"A": [[0, 4], [12, 4]], "B": [[0, 2], [11, 2], [11, 4], [12, 4]]}
SEAL5 = [[4, 4], [5, 4], [6, 4], [7, 4], [8, 4]]; SEAL7 = [[3, 4]] + SEAL5 + [[9, 4]]; SEAL9 = [[2, 4]] + SEAL7 + [[10, 4]]

add(2, 1, "미궁 입구", T2a, R2a,
    [W(3, "E01", "A", 4, 2.0), W(8, "E01", "B", 4, 2.0), W(25, "E04", "A", 3, 3.0), W(30, "E01", "B", 4, 1.5), W(50, "E04", "B", 3, 3.0),
     W(55, "E02", "A", 2, 3.0), W(75, "E04", "A", 2, 3.0), W(78, "E01", "B", 2, 1.5)],
    lives=5, deploy_limit=5, hero=[6, 6], note="고DEF 스켈레톤(E04) 소개. 파견대 없이 첫 출격.")
add(2, 2, "무너진 회랑", T2b, R2b,
    [W(3, "E01", "A", 4, 2.0), W(10, "E04", "B", 3, 3.0), W(30, "E04", "A", 3, 3.0), W(35, "E02", "B", 3, 2.5), W(55, "E01", "A", 5, 1.5),
     W(60, "E04", "B", 3, 3.0), W(85, "E04_elite", "A", 1, 0), W(86, "E02", "A", 2, 3.0), W(90, "E01", "B", 2, 1.5)],
    lives=5, deploy_limit=5, hero=[5, 6], npc=[npc("NPC_YUNCHAE", "L_SNIPER_YUNCHAE", (6, 5), "S", 20)],
    first_clear={"gem": 10, "scenario": "SC-04"}, note="윤채 NPC가 중앙 고지대에서 양쪽 길을 쏜다 → SC-04.")
add(2, 3, "주술사의 방", T2a, R2a,
    [W(3, "E04", "A", 3, 3.0), W(8, "E01", "B", 4, 2.0), W(25, "E05", "A", 2, 4.0), W(30, "E04", "B", 3, 3.0), W(50, "E05", "B", 2, 4.0),
     W(55, "E01", "A", 4, 1.5), W(75, "E05", "A", 2, 4.0), W(78, "E04", "B", 2, 3.0), W(80, "E01", "B", 2, 1.5)],
    lives=5, deploy_limit=6, hero=[6, 2], note="마법 원거리(E05)가 고지대 군단원을 노린다 — 치유 필요.")
add(2, 4, "뼈의 창고", T2c, R2c,
    [W(3, "E04", "A", 3, 3.0), W(6, "E01", "B", 4, 2.0), W(10, "E04", "C", 2, 3.0), W(30, "E05", "A", 1, 0), W(35, "E04", "B", 2, 2.5),
     W(40, "E01", "C", 3, 1.5), W(60, "E05", "C", 1, 0), W(62, "E04_elite", "B", 1, 0), W(65, "E04", "A", 2, 2.5), W(85, "E05", "B", 1, 0),
     W(88, "E01", "A", 2, 1.5), W(90, "E04", "C", 1, 0)],
    lives=5, deploy_limit=6, initial_dp=12, hero=[6, 4],
    unlock={"id": "SC-H03", "condition": "hero_kill_all:E05", "unit": "L_SNIPER_BONE", "hint": "주술사를 전부 직접 쓰러뜨릴 것"},
    note="3경로. 주술사 전원을 주인공이 처치하면 H03(본).")
add(2, 5, "구조 요청", T2b, R2b,
    [W(3, "E04", "A", 3, 3.0), W(8, "E05", "B", 1, 0), W(30, "E04", "B", 3, 2.5), W(35, "E01", "A", 4, 1.5), W(55, "E05", "A", 2, 3.5),
     W(60, "E04", "B", 3, 3.0), W(80, "E04_elite", "A", 1, 0), W(82, "E05", "B", 1, 0), W(85, "E04", "A", 2, 3.0), W(88, "E01", "A", 3, 1.5)],
    lives=5, deploy_limit=6, hero=[5, 6], npc=[npc("NPC_HAYUL", "L_MEDIC_HAYUL", (6, 3), "N", 20)],
    first_clear={"gem": 10, "scenario": "SC-05"}, note="고립된 구조대의 하율 NPC가 치유한다 → SC-05.")
add(2, 6, "거인의 통로", T2d, R2d,
    [W(3, "E04", "A", 3, 3.0), W(8, "E01", "B", 4, 2.0), W(25, "E06", "A", 1, 0), W(28, "E04", "B", 3, 3.0), W(50, "E06", "B", 1, 0),
     W(52, "E05", "A", 2, 4.0), W(75, "E06", "A", 1, 0), W(76, "E04", "A", 2, 3.0), W(78, "E04", "B", 3, 3.0)],
    lives=5, deploy_limit=6, initial_dp=12, hero=[6, 5], note="거대 오크(E06, 중량 4)가 좁은 길을 메운다 — 저지 3 필요.")
add(2, 7, "세 갈래 길", T2c2, R2c2,
    [W(3, "E01", "A", 4, 1.5), W(6, "E04", "B", 3, 3.0), W(10, "E04", "C", 2, 3.0), W(30, "E05", "A", 1, 0), W(33, "E06", "B", 1, 0),
     W(36, "E01", "C", 4, 1.5), W(55, "E04", "A", 2, 2.5), W(58, "E05", "C", 2, 3.5), W(62, "E04_elite", "B", 1, 0), W(80, "E04", "C", 2, 3.0),
     W(82, "E04", "A", 2, 3.0), W(85, "E01", "B", 3, 1.5), W(102, "E04", "B", 2, 3.0)],
    lives=5, deploy_limit=7, initial_dp=12, hero=[6, 6], note="B가 C의 방어 지점으로 합류(통로). 군단 8명이 처음 다 필요하다.")
add(2, 8, "백골 기사단장", TB, RB,
    [W(3, "E04", "A", 3, 3.0), W(20, "B02", "A", 1, 0), W(35, "E04", "B", 2, 2.0), W(50, "E05", "B", 1, 0), W(65, "E04", "A", 2, 2.0),
     W(80, "E04", "B", 2, 2.0), W(95, "E04_elite", "B", 1, 0), W(96, "E05", "B", 1, 0), W(110, "E04", "A", 2, 2.0), W(125, "E04", "B", 2, 2.0),
     W(140, "E05_elite", "B", 1, 0), W(141, "E04", "B", 2, 2.0), W(155, "E04", "A", 2, 2.0)],
    lives=3, deploy_limit=7, initial_dp=15, hero=[9, 4], sealed=SEAL5,
    boss={"id": "B02", "name": "백골 기사단장", "route": "A", "spawn_t": 20,
          "phases": [{"hp_above": 0.5, "sealed": SEAL5, "summon_every": 15, "summon": ["E04", 2]},
                     {"hp_above": 0.0, "sealed": SEAL7, "def_mult": 1.5, "summon_every": 10, "summon": ["E04", 3], "on_enter": ["invuln_2s"]}],
          "enrage_unblocked_speed_mult": 2.0},
    unlock={"id": "SC-H04", "condition": "hero_kill:B02 & stars:3", "unit": "L_SPEAR_MORS", "hint": "기사단장을 직접 쓰러뜨리고 ★3"},
    first_clear={"gem": 30, "skill_point": 1, "rank": "C", "level_cap": 35},
    challenge={"mods": ["deploy_limit-2", "dp_regen-30"]},
    note="돌진 보스. 2페이즈 DEF +50% → 술사 화력 필요. 소환물은 B 경로.")

# ======================================================================= 3장 길드 — 도심
T3a = ["XXXXXXXXXXXXX", "SGGGGGGGGGGPD", "XHHHXXXXXHHHX", "XHHHXXXXXHHHX", "XHHHXXXXXHHHX", "SGGGGGGGGGGPD", "XXXXXXXXXXXXX", "XXXXXXXXXXXXX"]
T3b = ["XXXXXXXXXXXXX", "SGGGPPGGGGGPD", "XXHHXXXXHHXXX", "XXXXXXXXXXXXX", "XXHHXXXXHHXXX", "SGGGPPGGGGGPD", "XXXXXXXXXXXXX", "XXXXXXXXXXXXX"]
T3c = ["XXXXXXXXXXXXX", "SGGGGGGGGGGPD", "XHHXHHXHHXHHX", "SGGGGGGGGGGPD", "XHHXHHXHHXHHX", "SGGGGGGGGGGPD", "XHHXHHXHHXHHX", "SGGGGGGGGGGPD"]
R3c = {"A": [[0, 6], [12, 6]], "B": [[0, 4], [12, 4]], "C": [[0, 2], [12, 2]], "D": [[0, 0], [12, 0]]}
T3d = ["XXXXXXXXXXXXX", "SGGGLLGGGGGPD", "XXHHXXXXXHHXX", "SGGGPPGGGGGPD", "XXHHXXXXXHHXX", "SGGGLLGGGGGPD", "XXXXXXXXXXXXX", "XXXXXXXXXXXXX"]
R3d = {"A": [[0, 6], [12, 6]], "B": [[0, 4], [12, 4]], "C": [[0, 2], [12, 2]]}
T3e = ["XXXXXXXXXXXXX", "SGGGGGGGGGGPD", "XHHXHHXHHXHHX", "SGGGGGGGGGGPD", "XHHXHHXHHXHHX", "SGGGGGGGGGGPD", "XXXXXXXXXXXXX", "XXXXXXXXXXXXX"]
T3f = ["XXXXXXXXXXXXX", "SGGGGGGGGGGPD", "XHHXXXXXXHHPX", "SGGGGGGGGGGPX", "XHHXXXXXXHHXX", "SGGGGGGGGGGPD", "XXXXXXXXXXXXX", "XXXXXXXXXXXXX"]
R3f = {"A": [[0, 6], [12, 6]], "B": [[0, 4], [11, 4], [11, 6], [12, 6]], "C": [[0, 2], [12, 2]]}
T3g = ["XXXXXXXXXXXXX", "XHHXXXXXXHHXX", "SGGGGGGGGGGPD", "XXXXLLLLLXXXX", "SGGGGGGGGGGPD", "XHHXXXXXXHHXX", "XXXXXXXXXXXXX", "XXXXXXXXXXXXX"]
R3g = {"A": [[0, 5], [12, 5]], "B": [[0, 3], [12, 3]]}

add(3, 1, "스카우트", T3a, R2a,
    [W(3, "E11", "A", 4, 2.0), W(8, "E11", "B", 4, 2.0), W(28, "E11", "A", 5, 1.8), W(32, "E02", "B", 3, 2.5), W(55, "E11", "B", 5, 1.8),
     W(58, "E02", "A", 3, 2.5), W(80, "E11_elite", "A", 1, 0), W(82, "E11", "B", 3, 1.5)],
    lives=5, deploy_limit=6, hero=[6, 6], note="길드 용병(인간 적) 소개. 옥상 고지대가 넓다.")
add(3, 2, "그림자 거리", T3b, R2a,
    [W(3, "E11", "A", 4, 2.0), W(8, "E11", "B", 3, 2.0), W(25, "E09", "A", 2, 4.0), W(30, "E11", "B", 4, 1.8), W(50, "E09", "B", 2, 4.0),
     W(55, "E02", "A", 3, 2.5), W(75, "E09", "A", 2, 4.0), W(78, "E11", "B", 4, 1.8), W(80, "E09", "B", 2, 4.0)],
    lives=5, deploy_limit=6, hero=[7, 6],
    unlock={"id": "SC-H05", "condition": "kill_while_blocked_all:E09", "unit": "L_SPEAR_HANSOL", "hint": "배신 헌터를 저지한 상태에서만 쓰러뜨릴 것"},
    note="은신(E09): 저지 전엔 원거리 표적 불가. 통로(P) 구간에서는 주인공이 설 수 없어 군단 저지가 필요.")
add(3, 3, "술사의 시험", T3a, R2a,
    [W(3, "E11", "A", 4, 2.0), W(8, "E04", "B", 3, 3.0), W(28, "E11", "B", 5, 1.8), W(32, "E04", "A", 4, 2.5), W(55, "E09", "A", 2, 4.0),
     W(58, "E04", "B", 4, 2.5), W(80, "E11_elite", "B", 1, 0), W(82, "E04", "A", 4, 2.5), W(85, "E11", "B", 3, 1.5)],
    lives=5, deploy_limit=6, hero=[6, 2], npc=[npc("NPC_YUNA", "L_CASTER_YUNA", (2, 4), "E", 25)],
    first_clear={"gem": 10, "scenario": "SC-06"}, note="고DEF 용병 · 스켈레톤을 유나 NPC의 마법이 뚫는다 → SC-06.")
add(3, 4, "옥상 추격", T3c, R3c,
    [W(3, "E11", "A", 3, 2.0), W(5, "E11", "C", 3, 2.0), W(10, "E02", "B", 2, 2.5), W(12, "E02", "D", 2, 2.5), W(35, "E09", "A", 1, 0),
     W(38, "E11", "B", 3, 1.8), W(40, "E11", "D", 2, 1.8), W(60, "E09", "C", 1, 0), W(62, "E02", "A", 2, 2.5), W(65, "E11_elite", "B", 1, 0),
     W(85, "E11", "C", 3, 1.8), W(88, "E09", "D", 1, 0), W(90, "E02", "B", 2, 2.5)],
    lives=5, deploy_limit=7, initial_dp=12, hero=[6, 4], note="출현 4 · 고지대 다수. 길드의 포위.")
add(3, 5, "길드 창고", T3d, R3d,
    [W(3, "E11", "A", 4, 2.0), W(6, "E11", "B", 4, 2.0), W(10, "E04", "C", 3, 3.0), W(30, "E09", "A", 2, 4.0), W(33, "E11", "C", 5, 1.8),
     W(36, "E02", "B", 3, 2.5), W(58, "E11_elite", "A", 1, 0), W(60, "E04", "B", 4, 2.5), W(62, "E09", "C", 2, 4.0), W(85, "E11", "A", 4, 1.8),
     W(88, "E11", "B", 3, 1.8), W(90, "E09", "C", 2, 4.0)],
    lives=5, deploy_limit=7, initial_dp=12, hero=[7, 4], note="봉인(L) · 통로(P) 혼합. 낙인 연구 자료 발견.")
add(3, 6, "이탈자", T3e, R2c,
    [W(3, "E11", "A", 4, 2.0), W(6, "E09", "B", 1, 0), W(10, "E11", "C", 3, 2.0), W(30, "E09_elite", "A", 1, 0), W(32, "E11", "B", 3, 1.8),
     W(35, "E02", "C", 2, 2.5), W(55, "E09", "A", 1, 0), W(58, "E09_elite", "B", 1, 0), W(59, "E09", "C", 1, 0), W(60, "E11", "B", 2, 1.8), W(80, "E09", "B", 1, 0),
     W(82, "E11", "A", 3, 1.8), W(85, "E11", "C", 3, 1.8)],
    lives=5, deploy_limit=7, initial_dp=12, hero=[6, 4], npc=[npc("NPC_TAEO", "L_SPECIAL_TAEO", (9, 2), "W", 25)],
    first_clear={"gem": 10, "scenario": "SC-07"}, note="태오 NPC(쾌속 재소집)가 아래 길을 맡는다 → SC-07.")
add(3, 7, "병원 봉쇄", T3f, R3f,
    [W(3, "E11", "A", 4, 2.0), W(6, "E11", "B", 4, 2.0), W(10, "E04", "C", 3, 3.0), W(30, "E09", "A", 2, 4.0), W(33, "E11", "C", 5, 1.8),
     W(36, "E02", "B", 3, 2.5), W(55, "E11_elite", "B", 1, 0), W(58, "E09", "C", 1, 0), W(60, "E11", "A", 3, 1.8), W(80, "E11", "B", 3, 1.8),
     W(83, "E09", "A", 1, 0), W(85, "E04", "C", 2, 3.0), W(100, "E11_elite", "C", 1, 0), W(102, "E11", "A", 2, 1.5)],
    lives=5, deploy_limit=8, initial_dp=12, hero=[6, 6],
    npc=[npc("CIV_01", "CIVILIAN", (3, 6), "E", 1, "survivor"), npc("CIV_02", "CIVILIAN", (7, 4), "E", 1, "survivor"),
         npc("CIV_03", "CIVILIAN", (5, 2), "E", 1, "survivor"), npc("CIV_04", "CIVILIAN", (9, 2), "E", 1, "survivor")],
    unlock={"id": "SC-H06", "condition": "npc_alive_all:CIV_*", "unit": "L_MEDIC_YERIN", "hint": "병원 환자 4명을 모두 지킬 것"},
    note="동생 이서가 입원한 병원. 민간인 4명이 경로 위에 있다 [H06].")
add(3, 8, "배신 길드장", T3g, R3g,
    [W(3, "E11", "A", 3, 2.0), W(6, "E11", "B", 3, 2.0), W(20, "B03", "A", 1, 0), W(35, "B03_clone", "B", 2, 2.0), W(50, "E09", "B", 2, 3.0),
     W(65, "E11", "A", 3, 2.0), W(80, "B03_clone", "B", 2, 2.0), W(95, "E09_elite", "B", 1, 0), W(96, "E11", "B", 3, 2.0), W(110, "E11", "A", 3, 2.0),
     W(125, "B03_clone", "B", 3, 2.0), W(140, "E09", "A", 2, 3.0), W(155, "E11", "B", 3, 2.0)],
    lives=3, deploy_limit=8, initial_dp=15, hero=[9, 5],
    boss={"id": "B03", "name": "배신 길드장", "route": "A", "spawn_t": 20,
          "phases": [{"hp_above": 0.66, "sealed": []}, {"hp_above": 0.33, "sealed": [], "on_enter": ["invuln_2s"]}, {"hp_above": 0.0, "sealed": [], "on_enter": ["invuln_2s"]}],
          "enrage_unblocked_speed_mult": 2.0},
    first_clear={"gem": 30, "skill_point": 1, "rank": "B", "level_cap": 45},
    challenge={"mods": ["deploy_limit-2", "enemy_hp+30"]},
    note="은신 보스 + 분신(B 경로). 분신은 저지 전엔 원거리로 못 맞춘다 → 지상 저지 후 사격.")

# ======================================================================= 4장 붉은 게이트 — 숲 · 설원
T4a = ["XXXXXXXXXXXXX", "SGGGGGGGGGGPD", "XXHHXXXXXHHXX", "SXXXXXXXXXXXD", "XXHHXXXXXHHXX", "SGGGGGGGGGGPD", "XXXXXXXXXXXXX", "XXXXXXXXXXXXX"]
RA1 = {"F": [[0, 4], [12, 4]]}
T4b = ["XXXXXXXXXXXXX", "SGGGRRGGGGGPD", "XXHHXXXXXHHXX", "XXXXXXXXXXXXX", "XXHHXXXXXHHXX", "SGGGRRGGGGGPD", "XXXXXXXXXXXXX", "XXXXXXXXXXXXX"]
T4c = ["XXXXXXXXXXXXX", "SGGGGGGGGGGPD", "XHHXXXXXXHHXX", "SGGGGGGGGGGPD", "XHHXXXXXXHHXX", "SGGGGGGGGGGPD", "XXXXXXXXXXXXX", "XXXXXXXXXXXXX"]
T4d = ["XXXXXXXXXXXXX", "SGGTGGGTGGGPD", "XXHHXXXXXHHXX", "SXXXXXXXXXXXD", "XXHHXXXXXHHXX", "SGGTGGGTGGGPD", "XXXXXXXXXXXXX", "XXXXXXXXXXXXX"]
T4f = ["SXXXXXXXXXXXD", "SGGGGGGGGGGPD", "XXHHXXXXXHHXX", "XXXXXXXXXXXXX", "XXHHXXXXXHHXX", "SGGGGGGGGGGPD", "SXXXXXXXXXXXD", "XXXXXXXXXXXXX"]
RA2 = {"F1": [[0, 7], [12, 7]], "F2": [[0, 1], [12, 1]]}
T4g = ["XXXXXXXXXXXXX", "SGGAAGGGGGGPD", "XHHXXXXXXHHXX", "SGGGGGAAGGGPD", "XHHXXXXXXHHXX", "SGGGGGGGGAAPD", "SXXXXXXXXXXXD", "XXXXXXXXXXXXX"]
RA3 = {"F": [[0, 1], [12, 1]]}
T4h = ["XXXXXXXXXXXXX", "XHHXXHHHXHHXX", "XGGGGGGGGGGGX", "SPGGLLLLLGGPD", "XGGGGGGGGGGGX", "SXXXXXXXXXXXD", "XHHXXHHHXHHXX", "XXXXXXXXXXXXX"]
R4h = {"A": [[0, 4], [12, 4]]}; RA4 = {"F": [[0, 2], [12, 2]]}

add(4, 1, "붉은 문", T4a, R2a,
    [W(3, "E14", "A", 2, 3.0), W(8, "E01", "B", 4, 2.0), W(20, "E07", "F", 4, 1.5), W(35, "E14", "B", 3, 3.0), W(40, "E07", "F", 5, 1.5),
     W(45, "E12", "A", 2, 3.0), W(65, "E14", "A", 3, 3.0), W(68, "E07", "F", 4, 1.5), W(85, "E14_elite", "B", 1, 0), W(87, "E07", "F", 2, 1.5)],
    routes_air=RA1, lives=5, deploy_limit=6, hero=[6, 6], note="비행(E07) 소개 — 비행 경로(F)는 지상 저지 불가, 사수 필수. 폐쇄형 게이트.")
add(4, 2, "정령의 숲", T4b, R2a,
    [W(3, "E14", "A", 3, 3.0), W(8, "E12", "B", 2, 3.0), W(28, "E07_swarm", "A", 2, 4.0), W(32, "E14", "B", 3, 3.0), W(52, "E12", "A", 2, 3.0),
     W(55, "E07_swarm", "B", 2, 4.0), W(75, "E14_elite", "A", 1, 0), W(77, "E14", "B", 2, 3.0), W(80, "E12", "A", 2, 3.0), W(95, "E14", "B", 2, 3.0), W(97, "E12", "B", 2, 3.0)],
    lives=5, deploy_limit=6, hero=[7, 6],
    unlock={"id": "SC-H08", "condition": "tile_hold:R,3,20", "unit": "L_SUPPORT_MOSS", "hint": "치유 타일 위에 군단원 3명을 20초 유지"},
    note="치유 타일(R) 소개. 박쥐 군단(E07_swarm)은 지상 경로를 날아온다.")
add(4, 3, "오크 요새", T4c, R2c,
    [W(3, "E12", "A", 3, 3.0), W(6, "E12", "C", 3, 3.0), W(10, "E14", "B", 2, 3.0), W(30, "E13", "A", 2, 4.0), W(33, "E12", "B", 4, 2.5),
     W(36, "E14", "C", 3, 3.0), W(58, "E12", "A", 4, 2.5), W(60, "E13", "C", 2, 4.0), W(62, "E14_elite", "B", 1, 0), W(85, "E12", "B", 3, 2.5),
     W(88, "E13", "A", 2, 4.0), W(90, "E12", "C", 4, 2.5), W(92, "E14", "A", 1, 0)],
    lives=5, deploy_limit=7, initial_dp=12, hero=[6, 4], npc=[npc("NPC_GRUSH", "L_SPEAR_GRUSH", (8, 2), "W", 35)],
    first_clear={"gem": 10, "scenario": "SC-08"}, note="엘프가 오크 마을을 친다. 그루쉬 NPC가 아래 길을 막고 주인공이 오크 편에 선다 → SC-08.")
add(4, 4, "함정 길", T4d, R2a,
    [W(3, "E12", "A", 3, 3.0), W(8, "E14", "B", 3, 3.0), W(20, "E07", "F", 5, 1.5), W(35, "E12", "B", 4, 2.5), W(38, "E13", "A", 2, 4.0),
     W(55, "E07", "F", 5, 1.5), W(60, "E14", "A", 3, 3.0), W(63, "E12", "B", 3, 2.5), W(85, "E13_elite", "A", 1, 0), W(87, "E07", "F", 3, 1.5), W(90, "E14", "B", 3, 3.0)],
    routes_air=RA1, lives=5, deploy_limit=7, initial_dp=12, hero=[6, 6], note="함정 타일(T): 처음 밟는 적에게 고정 피해. 엘프의 함정을 역이용.")
add(4, 5, "암살자의 숲", T4c, R2c,
    [W(3, "E12", "A", 3, 3.0), W(6, "E12_hidden", "B", 2, 4.0), W(10, "E14", "C", 2, 3.0), W(30, "E13", "A", 2, 3.5), W(33, "E12_hidden", "C", 2, 4.0),
     W(36, "E12", "B", 3, 2.5), W(58, "E13", "B", 2, 3.5), W(60, "E12_hidden", "A", 2, 4.0), W(62, "E14", "C", 2, 3.0), W(85, "E13_elite", "C", 1, 0),
     W(87, "E13", "A", 2, 3.5), W(90, "E12", "B", 2, 2.5)],
    lives=5, deploy_limit=7, initial_dp=12, hero=[6, 4],
    unlock={"id": "SC-H07", "condition": "kill_by_highground_all:E12_hidden", "unit": "L_SPECIAL_SILVA", "hint": "잠복 사수를 전부 고지대 사격으로 처치"},
    note="은신 엘프가 3경로로 온다. 저지 후 고지대 사격으로만 잡히는 잠복 사수 [H07].")
add(4, 6, "엘프 전초", T4f, R2a,
    [W(3, "E07", "F1", 3, 2.5), W(5, "E07", "F2", 3, 2.5), W(10, "E12", "A", 3, 3.0), W(14, "E14", "B", 2, 3.0), W(35, "E07_swarm", "F1", 3, 2.5),
     W(38, "E07_swarm", "F2", 3, 2.5), W(42, "E13", "A", 2, 4.0), W(60, "E07", "F1", 4, 2.0), W(62, "E07", "F2", 4, 2.0), W(65, "E12", "B", 3, 2.5),
     W(85, "E07_swarm", "F1", 3, 2.5), W(88, "E07_swarm", "F2", 3, 2.5), W(90, "E14_elite", "A", 1, 0), W(92, "E12", "B", 2, 2.5)],
    routes_air=RA2, lives=5, deploy_limit=7, initial_dp=12, hero=[6, 6], npc=[npc("NPC_EIR", "L_SNIPER_EIR", (9, 3), "S", 40)],
    first_clear={"gem": 10, "scenario": "SC-09"}, note="비행 파도 2경로. 에이르 NPC(대공)가 없으면 못 막는 구성 → SC-09.")
add(4, 7, "설원 횡단", T4g, {"A": [[0, 6], [12, 6]], "B": [[0, 4], [12, 4]], "C": [[0, 2], [12, 2]]},
    [W(3, "E14", "A", 3, 3.0), W(6, "E12", "B", 3, 3.0), W(10, "E13", "C", 2, 4.0), W(14, "E07", "F", 3, 2.5), W(35, "E14", "B", 3, 3.0),
     W(38, "E12", "C", 3, 2.5), W(40, "E07_swarm", "F", 3, 2.5), W(43, "E13", "A", 2, 3.5), W(62, "E14_elite", "C", 1, 0), W(64, "E12", "A", 3, 2.5),
     W(66, "E07", "F", 3, 2.5), W(68, "E13", "B", 2, 3.5), W(90, "E14", "A", 3, 3.0), W(92, "E13_elite", "B", 1, 0), W(94, "E12", "C", 3, 2.5), W(96, "E07", "F", 3, 2.5)],
    routes_air=RA3, lives=5, deploy_limit=8, initial_dp=12, hero=[6, 4], note="가속 타일(A) · 비행 + 지상 혼합. 붉은 게이트의 심장으로.")
add(4, 8, "붉은 게이트 수호수", T4h, R4h,
    [W(3, "E12", "A", 3, 3.0), W(20, "B04", "A", 1, 0), W(35, "E07", "F", 3, 1.5), W(50, "E14", "A", 2, 3.0), W(65, "E07", "F", 4, 1.5),
     W(80, "E12", "A", 3, 3.0), W(95, "E07_swarm", "F", 3, 1.5), W(110, "E14_elite", "A", 1, 0), W(125, "E07", "F", 4, 1.5), W(140, "E12", "A", 3, 3.0),
     W(155, "E07_swarm", "F", 4, 1.5), W(170, "E14", "A", 2, 3.0), W(185, "E07", "F", 3, 1.5)],
    routes_air=RA4, lives=3, deploy_limit=8, initial_dp=15, hero=[9, 4], sealed=SEAL5,
    boss={"id": "B04", "name": "붉은 게이트 수호수", "route": "A", "spawn_t": 20,
          "phases": [{"hp_above": 0.66, "sealed": SEAL5, "flying": True, "speed_mult": 0.0, "hover_idx": 6, "summon_every": 15, "summon": ["E07", 3]},
                     {"hp_above": 0.33, "sealed": SEAL5, "flying": False, "speed_mult": 1.0, "on_enter": ["invuln_2s"], "summon_every": 15, "summon": ["E07", 3]},
                     {"hp_above": 0.0, "sealed": SEAL7, "flying": True, "speed_mult": 0.0, "hover_idx": 6, "on_enter": ["invuln_2s"], "summon_every": 10, "summon": ["E07_swarm", 4]}]},
    first_clear={"gem": 30, "skill_point": 1, "level_cap": 45},
    challenge={"mods": ["deploy_limit-2", "enemy_hp+30"]},
    note="비행 → 착지(33~66%) → 비행. 날 때는 전장 중앙 상공에서 선회(전진 없음)하며 사수 · 술사만 유효, 착지하면 봉인 구역에서 걸어 나와 주인공이 집중. 중앙 고지대 6칸이 선회 지점을 쏜다. 문이 열린다.")

# ======================================================================= 5장 군단주 — 고대 사원
T5a = ["XXXXXXXXXXXXX", "SGGGGGGGGGGPD", "XXHHXLLXXHHXX", "XXXXXLLXXXXXX", "XXHHXLLXXHHXX", "SGGGGGGGGGGPD", "XXXXXXXXXXXXX", "XXXXXXXXXXXXX"]
T5b = ["XXXXXXXXXXXXX", "SGGLLLGGLLGPD", "XXHHXXXXXHHXX", "XXXXXXXXXXXXX", "XXHHXXXXXHHXX", "SGLLGGGLLLGPD", "XXXXXXXXXXXXX", "XXXXXXXXXXXXX"]
T5c = ["XXXXXXXXXXXXX", "SGGGGGGGGGGPD", "XHHXXSXXXHHXX", "SGGGGGGGGGGPD", "XHHXXSXXXHHXX", "SGGGGGGGGGGPD", "XXXXXXXXXXXXX", "XXXXXXXXXXXXX"]
R5c = {"A": [[0, 6], [12, 6]], "B": [[0, 4], [12, 4]], "C": [[0, 2], [12, 2]], "P1": [[5, 5], [5, 4], [12, 4]], "P2": [[5, 3], [5, 2], [12, 2]]}
T5f = ["XXXXXXXXXXXXX", "SGGLLLGGLLGPD", "XXHHXXXXXHHXX", "XXXXXSXXXXXXX", "XXHHXGXXXHHXX", "SGLLGGGLLLGPD", "XXXXXXXXXXXXX", "XXXXXXXXXXXXX"]
R5f = {"A": [[0, 6], [12, 6]], "B": [[0, 2], [12, 2]], "P1": [[5, 4], [5, 2], [12, 2]]}
T5g = ["XXXXXXXXXXXXX", "SGGGGGGGGGGPD", "XHHXLLXXXHHPX", "SGGGLLGGGGGPX", "XHHXLLXXXHHPX", "SGGGGGGGGGGPD", "XHHXXXXXXHHPX", "SGGGLLGGGGGPX"]
R5g = {"A": [[0, 6], [12, 6]], "B": [[0, 4], [11, 4], [11, 6], [12, 6]], "C": [[0, 2], [12, 2]], "D": [[0, 0], [11, 0], [11, 2], [12, 2]]}

add(5, 1, "사원 입구", T5a, R2a,
    [W(3, "E15", "A", 2, 4.0), W(8, "E16", "B", 2, 3.0), W(28, "E15", "B", 2, 4.0), W(32, "E16", "A", 3, 3.0), W(35, "E05", "A", 2, 4.0),
     W(55, "E15", "A", 3, 4.0), W(58, "E16", "B", 3, 3.0), W(80, "E16_elite", "A", 1, 0), W(82, "E05", "B", 3, 3.5), W(85, "E15", "B", 2, 4.0), W(100, "E16", "A", 2, 3.0), W(102, "E16", "B", 2, 3.0)],
    lives=5, deploy_limit=7, initial_dp=12, hero=[6, 6], note="석상(E15, DEF 350 · RES 0) — 술사가 답. 사원 벽의 낙인 문양.")
add(5, 2, "봉인 회랑", T5b, R2a,
    [W(3, "E16", "A", 3, 3.0), W(8, "E15", "B", 2, 4.0), W(28, "E16", "B", 3, 3.0), W(32, "E05", "A", 2, 3.5), W(55, "E15", "A", 2, 4.0),
     W(58, "E16", "B", 3, 2.5), W(80, "E16_elite", "B", 1, 0), W(82, "E05", "A", 2, 3.5), W(85, "E16", "A", 2, 3.0), W(100, "E15", "B", 2, 4.0), W(102, "E16", "A", 2, 3.0), W(104, "E05", "B", 2, 3.5)],
    lives=5, deploy_limit=7, initial_dp=12, hero=[6, 6], note="봉인 타일(L)이 경로의 절반 — 주인공이 못 서는 길을 군단이 간다.")
add(5, 3, "제단", T5c, R5c,
    [W(3, "E16", "A", 3, 3.0), W(6, "E16", "C", 2, 3.0), W(10, "E15", "B", 2, 4.0), W(25, "E17", "P1", 2, 2.0), W(28, "E17", "P2", 2, 2.0),
     W(40, "E05", "A", 2, 3.5), W(43, "E16", "B", 2, 3.0), W(50, "E17", "P1", 2, 2.0), W(53, "E17", "P2", 2, 2.0), W(65, "E16_elite", "C", 1, 0),
     W(68, "E15", "A", 2, 4.0), W(75, "E17", "P1", 3, 2.0), W(78, "E17", "P2", 3, 2.0), W(95, "E16", "B", 2, 3.0), W(98, "E05", "C", 2, 3.5)],
    lives=5, deploy_limit=7, initial_dp=12, hero=[6, 4], note="제단(맵 중앙 출현 지점)이 소환물(E17)을 B · C 경로 중간에 뿜는다.")
add(5, 4, "무녀", T5a, R2a,
    [W(3, "E16", "A", 3, 3.0), W(8, "E16", "B", 3, 3.0), W(28, "E16_elite", "A", 1, 0), W(30, "E05", "B", 3, 3.5), W(50, "E16", "B", 4, 2.5),
     W(53, "E15", "A", 2, 4.0), W(75, "E16_elite", "B", 1, 0), W(77, "E16", "A", 4, 2.5), W(80, "E05", "A", 2, 3.5), W(100, "E16", "B", 3, 3.0), W(102, "E15", "B", 2, 4.0), W(104, "E16", "A", 2, 3.0)],
    lives=5, deploy_limit=7, initial_dp=12, hero=[6, 6], npc=[npc("NPC_RIN", "L_SUPPORT_RIN", (9, 3), "N", 45)],
    first_clear={"gem": 10, "scenario": "SC-10"}, note="린 NPC의 지원 버프. 낙인을 알아본다 → SC-10 (1막 미스터리 첫 단서).")
add(5, 5, "수호자들", T4c, R2c,
    [W(3, "E16", "A", 3, 3.0), W(6, "E16", "B", 3, 3.0), W(10, "E16", "C", 2, 3.0), W(30, "E16_elite", "A", 1, 0), W(32, "E15", "B", 2, 4.0),
     W(35, "E05", "C", 2, 3.5), W(55, "E16", "A", 3, 2.5), W(58, "E16_elite", "B", 1, 0), W(60, "E16", "C", 2, 2.5), W(80, "E15", "A", 2, 4.0),
     W(83, "E16", "B", 3, 2.5), W(86, "E16_elite", "C", 1, 0), W(100, "E05", "A", 2, 3.5), W(102, "E16", "B", 3, 3.0), W(104, "E16", "C", 2, 3.0)],
    lives=5, deploy_limit=8, initial_dp=12, hero=[6, 4], note="인간형 엘리트(사원 기사) 다수. 3경로.")
add(5, 6, "석상 정원", T5f, R5f,
    [W(3, "E15", "A", 2, 4.0), W(6, "E16", "B", 3, 3.0), W(25, "E17", "P1", 4, 1.0), W(30, "E15", "B", 3, 4.0), W(33, "E05", "A", 3, 3.5),
     W(50, "E17", "P1", 5, 1.0), W(55, "E16", "A", 4, 2.5), W(58, "E16_elite", "B", 1, 0), W(75, "E17", "P1", 5, 1.0), W(80, "E15", "A", 3, 4.0),
     W(83, "E16", "B", 4, 2.5), W(100, "E17", "P1", 4, 1.0), W(104, "E05", "A", 3, 3.5), W(106, "E15", "B", 2, 4.0)],
    lives=5, deploy_limit=8, initial_dp=12, hero=[6, 6],
    unlock={"id": "SC-H10", "condition": "deploy_on:L,3", "unit": "L_SHIELD_ATLAS", "hint": "봉인 타일에 군단원 3명 이상을 소집"},
    note="봉인 + 제단 소환 혼합 [H10 아틀라스].")
add(5, 7, "군단주의 문", T5g, R5g,
    [W(3, "E16", "A", 3, 3.0), W(5, "E15", "B", 2, 4.0), W(8, "E16", "C", 2, 3.0), W(10, "E05", "D", 2, 3.5), W(30, "E16", "A", 2, 3.0),
     W(32, "E16", "B", 2, 2.5), W(35, "E15", "C", 1, 0), W(38, "E16", "D", 2, 2.5), W(58, "E05", "A", 1, 0), W(60, "E16_elite", "C", 1, 0),
     W(62, "E16", "D", 2, 2.5), W(64, "E15", "A", 1, 0), W(85, "E16", "B", 2, 2.5), W(90, "E05", "C", 2, 3.5),
     W(92, "E16", "A", 3, 3.0), W(112, "E16", "C", 2, 3.0), W(114, "E16_elite", "B", 1, 0)],
    lives=5, deploy_limit=8, initial_dp=15, hero=[6, 6], note="4경로 · 방어 2. 1막 기믹 종합, 런칭 최고 난도 일반 스테이지.")
add(5, 8, "사원의 군단주", TB, RB,
    [W(3, "E16", "A", 3, 3.0), W(20, "B05", "A", 1, 0), W(35, "E17", "B", 3, 1.0), W(50, "E16", "B", 3, 2.0), W(65, "E17", "A", 3, 1.0),
     W(80, "E17", "B", 4, 1.0), W(95, "E16_elite", "B", 1, 0), W(96, "E05", "B", 2, 3.0), W(110, "E17", "A", 3, 1.0), W(125, "E16", "B", 3, 2.0),
     W(140, "E17", "B", 5, 1.0), W(155, "E16_elite", "B", 1, 0), W(156, "E17", "A", 3, 1.0), W(170, "E05", "B", 3, 3.0), W(185, "E17", "B", 4, 1.0), W(200, "E16", "A", 3, 2.0)],
    lives=3, deploy_limit=8, initial_dp=15, hero=[9, 4], sealed=SEAL5,
    boss={"id": "B05", "name": "사원의 군단주", "route": "A", "spawn_t": 20,
          "phases": [{"hp_above": 0.66, "sealed": SEAL5, "summon_every": 15, "summon": ["E17", 3]},
                     {"hp_above": 0.33, "sealed": SEAL7, "on_enter": ["invuln_2s"], "summon_every": 12, "summon": ["E17", 4]},
                     {"hp_above": 0.0, "sealed": SEAL9, "on_enter": ["invuln_2s"], "summon_every": 10, "summon": ["E17", 5]}],
          "enrage_unblocked_speed_mult": 1.5},
    unlock={"id": "SC-H09", "condition": "stars:3 & knockdowns:0", "unit": "L_SHIELD_GUARDION", "hint": "넉다운 없이 ★3"},
    first_clear={"gem": 50, "skill_point": 1, "rank": "A", "level_cap": 60},
    challenge={"mods": ["deploy_limit-2", "enemy_hp+30"]},
    note="봉인이 페이즈마다 넓어져(5 → 7 → 9칸) 주인공 활동 영역이 줄고, 마법 원거리로 고지대를 노린다. 1막의 모든 기믹을 군단이 대신한다 [H09].")

def main():
    os.makedirs(OUT, exist_ok=True)
    for s in S:
        with open(os.path.join(OUT, f"Stage_{s['id']}.json"), "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, indent=2)
    print(f"wrote {len(S)} stages (ch2-5) to {os.path.normpath(OUT)}")

if __name__ == "__main__":
    main()
