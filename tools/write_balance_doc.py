#!/usr/bin/env python3
"""docs/data/*.csv → docs/09_데이터_밸런스_시트.md (발췌 표 재생성). 실행: python3 -I tools/write_balance_doc.py"""
import csv, json, glob, os
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."); D = os.path.join(ROOT, "docs", "data")
def rows(n): return list(csv.DictReader(open(os.path.join(D, n), encoding='utf-8')))
def md(rs, cols, hdr=None, fmt=None):
    hdr = hdr or cols; out = ["| " + " | ".join(hdr) + " |", "| " + " | ".join(":-:" for _ in cols) + " |"]
    for r in rs: out.append("| " + " | ".join((fmt or {}).get(c, lambda v: v)(r[c]) for c in cols) + " |")
    return "\n".join(out)
hero = rows('hero_levels.csv'); gs = rows('hero_growth_states.csv'); leg = rows('legion_templates.csv'); en = rows('enemies_by_chapter.csv'); st = rows('stages.csv'); bo = rows('bosses.csv'); ru = rows('rules.csv')
th = lambda v: f"{int(float(v)):,}" if v.replace('.', '', 1).isdigit() else v
F1 = {'xp_to_next': th, 'xp_cumulative': th, 'hp': th, 'atk': th}; F2 = {'hp': th, 'atk': th, 'def': th}; F3 = {'hp': th, 'atk': th}; F4 = {'hp': th}
hero_s = [r for r in hero if int(r['level']) in (1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 60)]
leg_s = [r for r in leg if (r['rarity'], r['awaken'], r['level']) in (('4', '0', '1'), ('4', '0', '30'), ('4', '1', '50'), ('6', '2', '70'))]
en_s = [r for r in en if r['chapter'] in ('1', '5') and r['kind'] != 'boss' and '_' not in r['enemy_id']]
st_main = [r for r in st if not r['stage'].startswith('SC')]; st_sc = [r for r in st if r['stage'].startswith('SC')]
cap = {1: 15, 2: 25, 3: 35, 4: 45, 5: 60}
xp_cum = {int(r['level']): int(r['xp_cumulative']) for r in hero}
xp_need = [(ch, xp_cum[cap[ch]] - (xp_cum[cap[ch - 1]] if ch > 1 else 0)) for ch in cap]
stage_xp = {}; sc_xp = {}
for p in glob.glob(os.path.join(ROOT, 'unity', 'Data', 'Stages', 'Stage_*.json')):
    d = json.load(open(p, encoding='utf-8'))
    tgt = stage_xp if d.get('type') == 'main' else sc_xp
    tgt[d['chapter']] = tgt.get(d['chapter'], 0) + d['rewards']['xp']
keys = ('rules.dp_cap', 'rules.hero_kill_dp.normal', 'rules.hero_kill_dp.elite', 'rules.hero_kill_dp.boss', 'rules.sp_per_kill.normal', 'rules.refund', 'rules.redeploy_mult', 'rules.death_cooldown_mult', 'rules.min_damage_ratio', 'rules.natural_sp_per_s', 'hero.level_growth', 'hero.relocate_cd', 'hero.relocate_time', 'hero.knockdown', 'hero.revive_hp', 'hero.momentum.per_stack_atk', 'hero.momentum.max', 'hero.ult_flash.sp', 'hero.ult_flash.atk_mult', 'hero.stat_points_per_level', 'legion.level_growth', 'legion.awaken_mult', 'legion.rarity_mult', 'legion.rarity_cost_add', 'legion.skill_rank_mult')
rules_tbl = "\n".join(f"| `{r['key']}` | {r['value']} |" for r in ru if r['key'] in keys)
xp_tbl = "\n".join(f"| {ch} | {cap[ch]} | {need:,} | {stage_xp.get(ch, 0):,} | {sc_xp.get(ch, 0):,} | {round((stage_xp.get(ch, 0) + sc_xp.get(ch, 0)) / need * 100)}% |" for ch, need in xp_need)
shield_def = next(r['def'] for r in leg_s if r['class'] == 'shield' and r['rarity'] == '4' and r['awaken'] == '1')
knight_atk = next(r['atk'] for r in en if r['enemy_id'] == 'E16' and r['chapter'] == '5')
doc = f'''# 09. 데이터 · 밸런스 시트 — ARMY OF ONE (가칭)

> 목적: GDD에서 [시뮬]로 표시한 모든 수치를 **한 곳의 원본**에서 생성한 시트로 제공한다. 원본은 `tools/difficulty_sim/params.yaml`(규칙 · 주인공 · 클래스 · 로스터 · 성장 상태 · 편성), `unity/Data/Enemies.json`(적 · 보스), `unity/Data/Stages/*.json`(스테이지)이다. 시트는 `python3 -I tools/export_balance_sheets.py`, 이 문서는 `python3 -I tools/write_balance_doc.py`로 재생성하며 손으로 고치지 않는다.
> 상태: v1 (시뮬레이션 2차 보정 반영) · 작성일: 2026-11-03 · 선행: [02 GDD](02_게임기획서_GDD.md), [07](07_난이도_시뮬레이션_계획.md) · [08](08_난이도_시뮬레이션_결과.md)

---

## 1. 시트 목록

| 파일 (`docs/data/`) | 내용 | 행 | 원본 |
| :--- | :--- | :-: | :--- |
| `hero_levels.csv` | 주인공 레벨 1~60: 다음 레벨 XP · 누적 XP · 스탯 미배분 능력치 · 스탯 포인트 · 스킬 포인트 | {len(hero)} | params.hero |
| `hero_growth_states.csv` | 챕터별 성장 상태(G0 하한 · G1 권장 · G2 상한)의 주인공 실효치와 군단 성장 | {len(gs)} | params.growth_by_chapter |
| `legion_templates.csv` | 클래스 7 × 희귀도 ★3~6 × 각성 0~2 × 대표 레벨(1 · 15 · 30 · 50 · 70) 능력치 · 코스트 · 사거리 | {len(leg)} | params.classes · legion |
| `roster.csv` | 군단원 24 + 파견대 2 (클래스 · 희귀도 · 저지) | 26 | params.units |
| `enemies_by_chapter.csv` | 적 베이스 17 · 변형 13 · 보스 5 × 챕터 1~5 배율 적용 실효치 | {len(en)} | Enemies.json × StageDef.scale |
| `stages.csv` | 메인 {len(st_main)} + 참전 {len(st_sc)} 스테이지 경제: 생명 · 초기 DP · 회복 · 배치 제한 · 경로 · 적 수 · 마지막 스폰 · 편성 코스트 합 · 자연 회복 DP | {len(st)} | Stages + params.squads |
| `bosses.csv` | 보스 5 최종값 | 5 | Enemies.json |
| `rules.csv` | 규칙 상수 (DP · SP · 환급 · 재소집 · 기세 · 권능 · 스탯 효과 · 트리 노드 · 성장 계수) | {len(ru)} | params.rules · hero · legion · sim |

---

## 2. 규칙 상수 (발췌)

| 키 | 값 |
| :--- | :-: |
{rules_tbl}

전체는 `rules.csv`. 스탯 효과(`hero.stat_effects.*`)와 트리 노드(`hero.tree.*`)도 포함.

---

## 3. 주인공 레벨 곡선 (스탯 미배분)

`stat(L) = base × (1 + 0.035(L−1))`, 다음 레벨 XP `60 × L^1.4`.

{md(hero_s, ['level', 'xp_to_next', 'xp_cumulative', 'hp', 'atk', 'def', 'attack_interval', 'relocate_cd', 'stat_points'], ['Lv', '다음 XP', '누적 XP', 'HP', 'ATK', 'DEF', '공격 간격', '재배치 쿨', '스탯 pt'], F1)}

### 3.1 챕터별 XP 예산
| 챕터 | 레벨 상한 | 상한까지 필요 XP(구간) | 메인 8스테이지 첫 클리어 XP | 참전 시나리오 첫 클리어 XP | 합계 / 필요 |
| :-: | :-: | :-: | :-: | :-: | :-: |
{xp_tbl}

- 메인 + 참전 첫 클리어로 챕터 상한의 절반 안팎에 닿는다. 나머지는 자원 게이트(XP, 일 3회 × 400 × 배율)와 반복 클리어(40%)로 채운다 — "권장(G1)은 자연 성장, 상한(G2)은 파밍"이라는 07 §2.3의 정의와 맞는다. 08 §1 F7의 "자연 성장 = 1-8 시점 Lv.9"는 이 곡선 기준이다.

---

## 4. 성장 상태 (챕터별 G0 · G1 · G2)

{md(gs, ['chapter', 'state', 'hero_level', 'stat_alloc', 'tree', 'hp', 'atk', 'def', 'attack_interval', 'relocate_cd', 'block', 'range_front', 'cmd_dp_mult', 'legion_level', 'awaken', 'skill_rank'], ['Ch', '상태', 'Lv', '스탯 배분', '트리', 'HP', 'ATK', 'DEF', '간격', '쿨', '저지', '전방', '처치 DP×', '군단 Lv', '각성', '랭크'], F2)}

---

## 5. 클래스 템플릿 (발췌: ★4 각성 0 Lv.1 / ★4 각성 0 Lv.30 / ★4 각성 1 Lv.50 / ★6 각성 2 Lv.70)

{md(leg_s, ['class', 'rarity', 'awaken', 'level', 'hp', 'atk', 'def', 'res', 'block', 'cost', 'redeploy_s', 'attack_interval', 'range', 'damage', 'skill'], ['클래스', '★', '각성', 'Lv', 'HP', 'ATK', 'DEF', 'RES', '저지', '코스트', '재소집', '간격', '사거리', '유형', '스킬'], F2)}

- 성장식 `base × (1 + 0.03(L−1)) × 각성[1.0 · 1.2 · 1.4] × 희귀도[0.85 · 1.0 · 1.12 · 1.25]`. 각성 1에서 R3 → R3+.
- **DEF 성장 주의**: 방패 ★4 각성 1 Lv.50 DEF {shield_def} vs 5장 사원 기사 ATK {knight_atk} → 최소 피해 5%. 후반 물리 적은 방패에 거의 무력하므로 마법 · 원거리 · 비행 적이 챕터마다 필요하다(GDD §7.4).

---

## 6. 적 × 챕터 (발췌: 1장 · 5장 실효치)

{md(en_s, ['enemy_id', 'name', 'chapter', 'hp', 'atk', 'def', 'res', 'speed', 'flying', 'ranged_tiles', 'arts', 'attack_interval', 'first_stage'], ['ID', '이름', 'Ch', 'HP', 'ATK', 'DEF', 'RES', '속도', '비행', '원거리', '마법', '간격', '첫 등장'], F3)}

- 전체(변형 · 보스 · 2~4장)는 `enemies_by_chapter.csv`. 변형 규칙: 엘리트 HP ×2.0 · ATK ×1.4 · DEF ×1.3.
- 챕터 배율(StageDef.scale): 2장 1.15/1.12/1.09 · 3장 1.33/1.27/1.18 · 4장 1.54/1.45/1.27 · 5장 1.84/1.66/1.39 (HP/ATK/DEF). 보스는 미적용.

---

## 7. 보스

{md(bo, ['boss_id', 'name', 'hp', 'atk', 'def', 'res', 'speed', 'attack_interval', 'abilities', 'stage'], ['ID', '이름', 'HP', 'ATK', 'DEF', 'RES', '속도', '간격', '능력', '스테이지'], F4)}

---

## 8. 스테이지 경제 (메인 40)

{md(st_main, ['stage', 'name', 'lives', 'initial_dp', 'dp_regen', 'deploy_limit', 'routes', 'routes_air', 'enemy_total', 'last_spawn_s', 'cards_g1', 'squad_cost_sum', 'natural_dp_by_last_spawn', 'boss'], ['ID', '이름', '생명', '초기 DP', '회복', '배치', '경로', '비행', '적', '마지막 스폰(s)', '카드', '편성 코스트 합', '자연 DP', '보스'])}

- "자연 DP"는 초기 + 회복 × 마지막 스폰 시각. 여기에 주인공 처치 DP(스테이지당 10~30, 08 문서)가 더해진다. 편성 코스트 합이 자연 DP를 넘는 스테이지(2~5장 대부분)는 처치 DP와 귀환 환급 없이는 전원 소집이 불가능하다 — 의도된 압박이며 08 §8 F17의 경제 모드가 그 증거다.

### 8.1 참전 시나리오 ({len(st_sc)})

{md(st_sc, ['stage', 'name', 'lives', 'initial_dp', 'deploy_limit', 'routes', 'routes_air', 'enemy_total', 'last_spawn_s', 'cards_g1', 'squad_cost_sum'], ['ID', '이름', '생명', '초기 DP', '배치', '경로', '비행', '적', '마지막 스폰(s)', '카드', '편성 코스트 합'])}

---

## 9. 보정 이력

| 회차 | 대상 | 변경 | 근거 |
| :-: | :--- | :--- | :--- |
| 1차 (1장) | 적 베이스 | HP ×1.5 · ATK ×1.3 | 08 §1 F1 |
| 1차 (1장) | 보스 B01 | 25,000/450/0.35 → 40,000/300/0.28, 광폭화, 소환 경로 | 08 §1 F5 |
| 2차 (2~5장) | 챕터 배율 | 초과분 ×0.6 | 08 §8 F13 |
| 2차 | 원거리 적 간격 | 일반 1.5s · 마법 2.5s | 08 §8 F12 |
| 2차 | 비행 속도 | 1.6 → 1.1 (군단 1.0), 드론 1.2 | 08 §8 F8 |
| 2차 | 보스 B02~B05 | ATK 350~450, HP 48k/55k/80k/100k, 선회 · 광폭화 | 08 §8 F11 |
| 2차 | 챕터 초기 DP · 회복 | 12/15/18/20(+3 보스, +3 3경로) · 0.7/0.75/0.8/0.85 | 08 §8 F10 |

---

## 10. 갱신 절차
1. 수치는 `params.yaml` · `Enemies.json` · 생성기(`tools/gen_*_stagedefs.py`)에서만 바꾼다.
2. `python3 tools/gen_ch1_stagedefs.py && python3 tools/gen_ch2_5_stagedefs.py && python3 tools/gen_scenario_stagedefs.py && python3 tools/build_stage_index.py && python3 tools/stagedef_check.py`
3. `python3 -I tools/difficulty_sim/simulate.py --runs 300` → 08 문서 표 갱신(`write_results_*.py`).
4. `python3 -I tools/export_balance_sheets.py && python3 -I tools/write_balance_doc.py` → CSV와 이 문서 갱신.
5. GDD의 해당 절([시뮬] 표시)을 고친다.
'''
open(os.path.join(ROOT, 'docs', '09_데이터_밸런스_시트.md'), 'w', encoding='utf-8').write(doc); print("09 written", doc.count("\n"))
