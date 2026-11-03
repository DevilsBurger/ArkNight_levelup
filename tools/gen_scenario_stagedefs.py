#!/usr/bin/env python3
"""참전 시나리오 StageDef 생성기 — 메인 합류 10편(18스테이지) + 숨은 합류 10편(각 1스테이지) = 28 (04 문서 §5).
ID 규약: SC01-1 … (메인), SCH01-1 (숨은). 마지막 스테이지에는 대상 군단원이 NPC로 미리 배치된다.
시뮬레이터용 편성은 tools/difficulty_sim/squads_scenario.yaml 로 함께 출력한다."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from gen_ch1_stagedefs import stage, W, OUT
from gen_ch2_5_stagedefs import SCALE, T2a, R2a, T2b, R2b, T2c, R2c, T2d, R2d, T3a, T3b, T3c, R3c, T3e, T4a, RA1, T4b, T4c, T4f, RA2, T5a, T5b, T5c, R5c, npc
# 1장 템플릿
T1a = ["XXXXXXXXXXXXX", "XXXHHHXHHHXXX", "XXGGGGGGGGGXX", "XGGGGGGGGGGGX", "SPGGGGGGGGGPD", "XGGGGGGGGGGGX", "XXGGGGGGGGGXX", "XXXXXXXXXXXXX"]
R1a = {"A": [[0, 3], [12, 3]]}
T1b = ["XXXXXXXXXXXXX", "SGGGGGGGGGGGX", "XXHHXXXXXHHPX", "XXXXXXXXXXXPD", "XXHHXXXXXHHPX", "SGGGGGGGGGGGX", "XXXXXXXXXXXXX", "XXXXXXXXXXXXX"]
R1b = {"A": [[0, 6], [11, 6], [11, 4], [12, 4]], "B": [[0, 2], [11, 2], [11, 4], [12, 4]]}

POOL = {1: ["E01", "E02", "E03"], 2: ["E04", "E01", "E05"], 3: ["E11", "E09", "E02"], 4: ["E14", "E12", "E13"], 5: ["E16", "E15", "E05"]}
ELITE = {1: "E01_elite", 2: "E04_elite", 3: "E11_elite", 4: "E14_elite", 5: "E16_elite"}
INIT_DP = {1: 10, 2: 12, 3: 15, 4: 18, 5: 20}; REGEN = {1: 0.7, 2: 0.7, 3: 0.75, 4: 0.8, 5: 0.85}; LIMIT = {1: 5, 2: 6, 3: 7, 4: 7, 5: 8}

def auto_waves(ch, total, lanes, *, elite=1, t0=3.0, spacing=22.0, air_lane=None, air_count=0):
    """적 풀에서 total 마리를 레인에 교대로 배정. 엘리트는 마지막 1/3 구간."""
    pool = POOL[ch]; ws = []; left = total - elite - air_count; k = 0; t = t0
    spacing = spacing * (1.0 + 0.5 * (len(lanes) - 2))   # 경로가 많을수록 웨이브 간격을 벌린다 (DP 템포)
    while left > 0:
        lane = lanes[k % len(lanes)]; eid = pool[k % len(pool)] if k % 3 != 2 else pool[0]
        n = min(left, 3 if eid == pool[0] else 2)
        ws.append(W(t, eid, lane, n, 2.5)); left -= n; k += 1; t += spacing / len(lanes)
    for i in range(elite):
        ws.append(W(t + 5 + i * 10, ELITE[ch], lanes[i % len(lanes)], 1, 0))
    if air_lane and air_count:
        for i in range(0, air_count, 3):
            ws.append(W(25 + i * 8, "E07", air_lane, min(3, air_count - i), 2.0))
    return ws

S = []; SQ = {}
def add(sid, name, ch, rows, routes, waves, *, unit, scenario, last, npc_tile=None, npc_dir="E", squad, routes_air=None, hero=None, sealed=None, note=""):
    kw = dict(lives=5, initial_dp=INIT_DP[ch] + (3 if len(routes) >= 3 else 0), dp_regen=REGEN[ch], deploy_limit=LIMIT[ch], hero=hero,
              scale=SCALE.get(ch, {"hp": 1.0, "atk": 1.0, "def": 1.0}), chapter=ch, routes_air=routes_air, sealed=sealed,
              rewards={"xp": int(250 * {1: 1.0, 2: 1.25, 3: 1.55, 4: 1.9, 5: 2.4}[ch]), "gold": int(180 * {1: 1.0, 2: 1.25, 3: 1.55, 4: 1.9, 5: 2.4}[ch]), "drops": []},
              first_clear={"gem": 10, "join": unit} if last else {"gem": 0},
              challenge=None, note=note)
    if last and npc_tile:
        kw["npc"] = [npc(f"NPC_{unit.split('_')[-1]}", unit, npc_tile, npc_dir, {1: 12, 2: 25, 3: 35, 4: 45, 5: 50}[ch])]
    d = stage(sid, name, rows, routes, waves, **kw)
    d["type"] = "scenario"; d["scenario"] = scenario; d["join_unit"] = unit; d["is_last"] = last
    S.append(d); SQ[sid] = {"hero": "awakened", "legion": squad, "optional": []}

# ---------------- 메인 합류 10편 (04 §5.1) ----------------
# SC-01 첫 낙인 (도경) — 1-3 후, 1스테이지. 편성: 파견대. 도경이 중반 기립해 동행(NPC).
add("SC01-1", "첫 낙인", 1, T1a, R1a, auto_waves(1, 12, ["A"], elite=0, spacing=12), unit="L_SPEAR_DOKYUNG", scenario="SC-01", last=True,
    npc_tile=(8, 3), npc_dir="W", squad=["DSP_SPEAR", "DSP_SNIPER"], hero=[6, 3], note="쓰러진 도경을 업고 나오는 길. 도경 NPC가 중반 기립.")
# SC-02 방패 (무진) — 1-5 후, 2스테이지
add("SC02-1", "방패 I", 1, T1b, R1b, auto_waves(1, 18, ["A", "B"], elite=1, spacing=20), unit="L_SHIELD_MUJIN", scenario="SC-02", last=False,
    squad=["L_SPEAR_DOKYUNG", "DSP_SPEAR", "DSP_SNIPER"], hero=[6, 6], note="무진은 낙인을 경계한다.")
add("SC02-2", "방패 II", 1, T1b, R1b, auto_waves(1, 22, ["A", "B"], elite=1, spacing=18), unit="L_SHIELD_MUJIN", scenario="SC-02", last=True,
    npc_tile=(8, 2), npc_dir="W", squad=["L_SPEAR_DOKYUNG", "DSP_SPEAR", "DSP_SNIPER"], hero=[6, 6], note="주인공이 무진의 길을 대신 막아 준다 → 합류.")
# SC-03 예속 (킥) — 1-7 후
add("SC03-1", "예속", 1, T1b, R1b, auto_waves(1, 20, ["A", "B"], elite=1, spacing=18), unit="L_SPECIAL_KICK", scenario="SC-03", last=True,
    npc_tile=(4, 2), npc_dir="W", squad=["L_SPEAR_DOKYUNG", "L_SHIELD_MUJIN", "DSP_SPEAR", "DSP_SNIPER"], hero=[6, 6], note="도망치던 정찰병이 엎드린다. 킥 NPC(쾌속 재소집 시연).")
# SC-04 저격수 (윤채) — 2-2 후, 2스테이지
add("SC04-1", "저격수 I", 2, T2a, R2a, auto_waves(2, 22, ["A", "B"], elite=1), unit="L_SNIPER_YUNCHAE", scenario="SC-04", last=False,
    squad=["L_SPEAR_DOKYUNG", "L_SHIELD_MUJIN", "L_SPECIAL_KICK"], hero=[6, 6], note="협회 파견이 끝났는데도 윤채는 남는다.")
add("SC04-2", "저격수 II", 2, T2b, R2b, auto_waves(2, 26, ["A", "B"], elite=1), unit="L_SNIPER_YUNCHAE", scenario="SC-04", last=True,
    npc_tile=(6, 5), npc_dir="S", squad=["L_SPEAR_DOKYUNG", "L_SHIELD_MUJIN", "L_SPECIAL_KICK"], hero=[5, 6], note="고지대 사격으로 회랑 돌파 → 합류.")
# SC-05 구조대 (하율) — 2-5 후
add("SC05-1", "구조대", 2, T2d, R2d, auto_waves(2, 24, ["A", "B"], elite=1), unit="L_MEDIC_HAYUL", scenario="SC-05", last=True,
    npc_tile=(9, 6), npc_dir="S", squad=["L_SPEAR_DOKYUNG", "L_SHIELD_MUJIN", "L_SPECIAL_KICK", "L_SNIPER_YUNCHAE"], hero=[6, 5], note="치유 사거리 안에 아군을 세우는 법.")
# SC-06 술사의 시험 (유나) — 3-3 후, 2스테이지
add("SC06-1", "술사의 시험 I", 3, T3a, R2a, auto_waves(3, 20, ["A", "B"], elite=1), unit="L_CASTER_YUNA", scenario="SC-06", last=False,
    squad=["L_SPEAR_DOKYUNG", "L_SHIELD_MUJIN", "L_SPECIAL_KICK", "L_SNIPER_YUNCHAE", "L_MEDIC_HAYUL"], hero=[6, 6], note="길드가 유나에게 감시를 시킨다.")
add("SC06-2", "술사의 시험 II", 3, T3a, R2a, auto_waves(3, 24, ["A", "B"], elite=1), unit="L_CASTER_YUNA", scenario="SC-06", last=True,
    npc_tile=(2, 4), npc_dir="E", squad=["L_SPEAR_DOKYUNG", "L_SHIELD_MUJIN", "L_SPECIAL_KICK", "L_SNIPER_YUNCHAE", "L_MEDIC_HAYUL"], hero=[6, 2], note="고DEF 적을 유나의 마법이 뚫는다 → 합류.")
# SC-07 이탈자 (태오) — 3-6 후, 3연작
add("SC07-1", "이탈자 I", 3, T3b, R2a, auto_waves(3, 20, ["A", "B"], elite=1), unit="L_SPECIAL_TAEO", scenario="SC-07", last=False,
    squad=["L_SPEAR_DOKYUNG", "L_SHIELD_MUJIN", "L_SPECIAL_KICK", "L_SNIPER_YUNCHAE", "L_MEDIC_HAYUL", "L_CASTER_YUNA"], hero=[7, 6], note="길드장의 비밀을 들고 도망친 태오. 추격전.")
add("SC07-2", "이탈자 II", 3, T3e, R2c, auto_waves(3, 30, ["A", "B", "C"], elite=1), unit="L_SPECIAL_TAEO", scenario="SC-07", last=False,
    squad=["L_SPEAR_DOKYUNG", "L_SHIELD_MUJIN", "L_SPECIAL_KICK", "L_SNIPER_YUNCHAE", "L_MEDIC_HAYUL", "L_CASTER_YUNA"], hero=[6, 4], note="3경로 추격.")
add("SC07-3", "이탈자 III", 3, T3c, R3c, auto_waves(3, 26, ["A", "B", "C", "D"], elite=1), unit="L_SPECIAL_TAEO", scenario="SC-07", last=True,
    npc_tile=(9, 0), npc_dir="W", squad=["L_SPEAR_DOKYUNG", "L_SHIELD_MUJIN", "L_SPECIAL_KICK", "L_SNIPER_YUNCHAE", "L_MEDIC_HAYUL", "L_CASTER_YUNA"], hero=[6, 4], note="쾌속 재소집 퍼즐 — 태오 NPC가 4번째 길을 홀로 맡는다 → 합류.")
# SC-08 오크의 맹세 (그루쉬) — 4-3 후, 2스테이지
add("SC08-1", "오크의 맹세 I", 4, T4c, R2c, auto_waves(4, 24, ["A", "B", "C"], elite=1), unit="L_SPEAR_GRUSH", scenario="SC-08", last=False,
    squad=["L_SPEAR_DOKYUNG", "L_SHIELD_MUJIN", "L_SPECIAL_KICK", "L_SNIPER_YUNCHAE", "L_MEDIC_HAYUL", "L_CASTER_YUNA", "L_SPECIAL_TAEO"], hero=[6, 4], note="엘프에게서 오크 부족을 지킨다.")
add("SC08-2", "오크의 맹세 II", 4, T4a, R2a, auto_waves(4, 30, ["A", "B"], elite=2, air_lane="F", air_count=6), unit="L_SPEAR_GRUSH", scenario="SC-08", last=True,
    npc_tile=(8, 2), npc_dir="W", squad=["L_SPEAR_DOKYUNG", "L_SHIELD_MUJIN", "L_SPECIAL_KICK", "L_SNIPER_YUNCHAE", "L_MEDIC_HAYUL", "L_CASTER_YUNA", "L_SPECIAL_TAEO"], routes_air=RA1, hero=[6, 6], note="그루쉬 NPC(저지 3)가 아래 길을 막는다 → 맹세.")
# SC-09 엘프 전초 (에이르) — 4-6 후, 2스테이지
add("SC09-1", "엘프 전초 I", 4, T4a, R2a, auto_waves(4, 26, ["A", "B"], elite=1, air_lane="F", air_count=9), unit="L_SNIPER_EIR", scenario="SC-09", last=False,
    squad=["L_SPEAR_DOKYUNG", "L_SHIELD_MUJIN", "L_SPECIAL_KICK", "L_SNIPER_YUNCHAE", "L_MEDIC_HAYUL", "L_CASTER_YUNA", "L_SPECIAL_TAEO", "L_SPEAR_GRUSH"], routes_air=RA1, hero=[6, 6], note="비행 적의 파도.")
add("SC09-2", "엘프 전초 II", 4, T4f, R2a, auto_waves(4, 30, ["A", "B"], elite=1, air_lane="F1", air_count=9), unit="L_SNIPER_EIR", scenario="SC-09", last=True,
    npc_tile=(9, 3), npc_dir="S", squad=["L_SPEAR_DOKYUNG", "L_SHIELD_MUJIN", "L_SPECIAL_KICK", "L_SNIPER_YUNCHAE", "L_MEDIC_HAYUL", "L_CASTER_YUNA", "L_SPECIAL_TAEO", "L_SPEAR_GRUSH"], routes_air=RA2, hero=[6, 6], note="에이르 NPC(대공) 없이는 못 막는 구성 → 합류.")
# SC-10 무녀 (린) — 5-4 후, 2스테이지
add("SC10-1", "무녀 I", 5, T5a, R2a, auto_waves(5, 28, ["A", "B"], elite=1), unit="L_SUPPORT_RIN", scenario="SC-10", last=False,
    squad=["L_SHIELD_MUJIN", "L_SPECIAL_KICK", "L_SNIPER_YUNCHAE", "L_MEDIC_HAYUL", "L_CASTER_YUNA", "L_SPECIAL_TAEO", "L_SPEAR_GRUSH", "L_SNIPER_EIR"], hero=[6, 6], note="사원의 봉인을 지키던 무녀.")
add("SC10-2", "무녀 II", 5, T5b, R2a, auto_waves(5, 32, ["A", "B"], elite=2), unit="L_SUPPORT_RIN", scenario="SC-10", last=True,
    npc_tile=(9, 3), npc_dir="N", squad=["L_SHIELD_MUJIN", "L_SPECIAL_KICK", "L_SNIPER_YUNCHAE", "L_MEDIC_HAYUL", "L_CASTER_YUNA", "L_SPECIAL_TAEO", "L_SPEAR_GRUSH", "L_SNIPER_EIR"], hero=[6, 6], note="린이 낙인을 알아본다 — 1막 미스터리의 첫 단서 → 합류.")

# ---------------- 숨은 합류 10편 (04 §5.2) — 각 1스테이지 "낙인" ----------------
HID = [
    ("SCH01-1", "생존자", 1, T1b, R1b, 18, "L_SUPPORT_JOY", (8, 2), "W", ["L_SPEAR_DOKYUNG", "DSP_SPEAR", "DSP_SNIPER"], [6, 6]),
    ("SCH02-1", "포식자", 1, T1b, R1b, 22, "L_SPEAR_GROL", (8, 2), "W", ["L_SPEAR_DOKYUNG", "L_SHIELD_MUJIN", "DSP_SPEAR", "DSP_SNIPER"], [6, 6]),
    ("SCH03-1", "뼈의 사수", 2, T2a, R2a, 24, "L_SNIPER_BONE", (9, 5), "S", ["L_SPEAR_DOKYUNG", "L_SHIELD_MUJIN", "L_SPECIAL_KICK", "L_SNIPER_YUNCHAE"], [6, 6]),
    ("SCH04-1", "백골의 맹세", 2, T2d, R2d, 28, "L_SPEAR_MORS", (8, 3), "W", ["L_SPEAR_DOKYUNG", "L_SHIELD_MUJIN", "L_SPECIAL_KICK", "L_SNIPER_YUNCHAE", "L_MEDIC_HAYUL"], [6, 5]),
    ("SCH05-1", "거리의 복서", 3, T3b, R2a, 20, "L_SPEAR_HANSOL", (8, 2), "W", ["L_SPEAR_DOKYUNG", "L_SHIELD_MUJIN", "L_SPECIAL_KICK", "L_SNIPER_YUNCHAE", "L_MEDIC_HAYUL"], [7, 6]),
    ("SCH06-1", "길드 치유사", 3, T3a, R2a, 28, "L_MEDIC_YERIN", (10, 3), "W", ["L_SPEAR_DOKYUNG", "L_SHIELD_MUJIN", "L_SPECIAL_KICK", "L_SNIPER_YUNCHAE", "L_MEDIC_HAYUL", "L_CASTER_YUNA", "L_SPECIAL_TAEO"], [6, 6]),
    ("SCH07-1", "암살자", 4, T4c, R2c, 24, "L_SPECIAL_SILVA", (8, 2), "W", ["L_SPEAR_DOKYUNG", "L_SHIELD_MUJIN", "L_SPECIAL_KICK", "L_SNIPER_YUNCHAE", "L_MEDIC_HAYUL", "L_CASTER_YUNA", "L_SPECIAL_TAEO", "L_SPEAR_GRUSH"], [6, 4]),
    ("SCH08-1", "숲의 정령", 4, T4b, R2a, 26, "L_SUPPORT_MOSS", (9, 5), "S", ["L_SPEAR_DOKYUNG", "L_SHIELD_MUJIN", "L_SPECIAL_KICK", "L_SNIPER_YUNCHAE", "L_MEDIC_HAYUL", "L_CASTER_YUNA", "L_SPECIAL_TAEO"], [6, 6]),
    ("SCH09-1", "수호 기사", 5, T5c, R5c, 28, "L_SHIELD_GUARDION", (8, 4), "W", ["L_SHIELD_MUJIN", "L_SUPPORT_RIN", "L_SNIPER_YUNCHAE", "L_MEDIC_HAYUL", "L_CASTER_YUNA", "L_SPECIAL_TAEO", "L_SPEAR_GRUSH", "L_SNIPER_EIR"], [6, 6]),
    ("SCH10-1", "석상 골렘", 5, T5b, R2a, 30, "L_SHIELD_ATLAS", (8, 2), "W", ["L_SHIELD_MUJIN", "L_SUPPORT_RIN", "L_SNIPER_YUNCHAE", "L_MEDIC_HAYUL", "L_CASTER_YUNA", "L_SPECIAL_TAEO", "L_SPEAR_GRUSH", "L_SNIPER_EIR"], [6, 6]),
]
for sid, name, ch, rows, routes, total, unit, tile, d, squad, hero in HID:
    lanes = [k for k in routes if not k.startswith("P")]
    add(sid, name, ch, rows, routes, auto_waves(ch, total, lanes, elite=1), unit=unit, scenario="SC-H" + sid[3:5], last=True, npc_tile=tile, npc_dir=d, squad=squad, hero=hero,
        note="숨은 합류 '낙인' 스테이지 — 대상이 NPC로 동행한다.")

def main():
    os.makedirs(OUT, exist_ok=True)
    for s in S:
        with open(os.path.join(OUT, f"Stage_{s['id']}.json"), "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, indent=2)
    import yaml
    with open(os.path.join(os.path.dirname(__file__), "difficulty_sim", "squads_scenario.yaml"), "w", encoding="utf-8") as f:
        yaml.safe_dump({"squads_scenario": SQ}, f, allow_unicode=True, sort_keys=False)
    print(f"wrote {len(S)} scenario stages, squads for sim")

if __name__ == "__main__":
    main()
