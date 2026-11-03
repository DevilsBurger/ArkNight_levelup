"""results_sc.csv → 08 문서 §9(참전 시나리오 28스테이지) 마크다운을 표준 출력으로.
예) python3 -I tools/difficulty_sim/simulate.py --kind scenario --growth G1 --policies S,A,D --runs 300 --out tools/difficulty_sim/out/results_sc.csv
    python3 -I tools/difficulty_sim/write_results_scenario.py tools/difficulty_sim/out/results_sc.csv"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from report import load


def stage_key(s): return (s.startswith("SC"), [v.zfill(4) for v in s.split("-")])

rows = load(sys.argv[1])
stages = sorted({r["stage"] for r in rows}, key=stage_key)
by = {(r["stage"], r["policy"]): r for r in rows if r["growth"] == "G1"}


def g(s, pol, k): return float(by[(s, pol)][k])
def pc(x): return f"{x*100:.0f}%"


low = [s for s in stages if g(s, "D", "P_star3") < 0.5 or g(s, "D", "P_clear") < 0.9]
a_low = [s for s in stages if g(s, "A", "P_clear") < 0.6]
solo = [s for s in stages if g(s, "S", "P_star3") > 0.2]
lines = ["| 스테이지 | 이름 | D 클리어 | D ★3 | D 누수 | D 군단 이탈 | A 클리어 | A ★3 | S ★3 | T(s) |", "| :-: | :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |"]
for s in stages:
    d = by[(s, "D")]
    lines.append(f"| {s} | {d['name']} | {pc(g(s,'D','P_clear'))} | {pc(g(s,'D','P_star3'))} | {g(s,'D','leaks'):.2f} | {g(s,'D','legion_deaths'):.2f} | "
                 f"{pc(g(s,'A','P_clear'))} | {pc(g(s,'A','P_star3'))} | {pc(g(s,'S','P_star3'))} | {g(s,'D','T_mean'):.0f} |")
table = "\n".join(lines)

print(f"""
---

## 9. 참전 시나리오 28스테이지 (메인 합류 18 + 숨은 합류 10)

> `tools/gen_scenario_stagedefs.py`가 만든 28개 StageDef를 정책 S · A · D × 성장 G1(해당 챕터 권장)으로 셀당 300런. 참전 시나리오는 **군단원을 얻는 길**이라 메인보다 쉬워야 한다 — 목표: D 클리어 ≥ 90% · ★3 ≥ 70%, 초보(A) 클리어 ≥ 60%. 솔로 제약(R4)은 적용하지 않는다(마지막 스테이지는 합류 대상이 NPC로 같이 싸운다).

### 9.1 발견과 조치
| # | 발견 | 조치 |
| :-: | :--- | :--- |
| F20 | 1차: 3장 시나리오(SC06-1 3% · SC06-2 23% · SC07-1 23% · SCH05-1 21%)에서 **배신 헌터(E09, HP 4,200 · ATK 416)가 둘씩** 주인공 없는 레인에 들어와 저지(3★ 창병)를 녹이고 누수(군단 이탈 ≈ 1/런). 4장 SCH07-1(20%)은 오크 전사(E14) 셋씩 | 중량급(HP ≥ 3,500: E09 · E14 · E15)은 **한 마리씩**(풀 선두면 둘) — 5~6장 편성의 반대편 레인은 중량급 둘을 동시에 못 받는다 |
| F21 | 2차: 3경로 시나리오(SC08-1 76% → 24%)에서 레인 3개와 적 풀 3종이 **고정 짝**이 되어 한 레인에만 중량급이 몰리고, 주인공은 가벼운 적만 오는 레인에 서 있다가 경제 이동으로 자리를 비움 | 3경로 이상은 **중량급을 주인공 경로로**, 나머지를 다른 경로로 돌린다(`hero_lane`). 레벨 디자인 규칙 후보 R10: "주인공 기본 위치의 경로가 가장 무거운 적을 받는다" |

### 9.2 결과 (G1)
{table}

### 9.3 판정
- **D 클리어 < 90% 또는 ★3 < 50%**: {", ".join(low) if low else "없음"}.
- **D ★3 50~80%**: {", ".join(s for s in stages if 0.5 <= g(s, "D", "P_star3") < 0.8) or "없음"} — 3경로 · 긴 추격전 스테이지(SC07-3 80% · SCH10-1 89%도 경계). 시나리오 치고는 빡빡하지만 "얻기 어려운 군단원"(00 P4: 희귀도 = 시나리오 난이도)이라 유지하고 플레이테스트로 재판단.
- **초보(A) 클리어 < 60%**: {", ".join(a_low) if a_low else "없음"} — 3경로 시나리오는 초보가 절반 가까이 실패한다. 06 온보딩의 "권장 편성 자동 제안"과 재도전 안내(결과 창 "어디서 샜는가")가 이 스테이지들을 겨냥한다.
- **솔로(S) ★3 > 20%**: {len(solo)}/28 — 시나리오는 R4 대상이 아니다. 다만 1~2장 시나리오 대부분이 솔로 ★3 100%인 것은 "군단 없이도 군단원을 얻는다"는 뜻이라, 2장 이후 시나리오에 **군단 소집 조건**(특정 타일에 소집해야 열리는 문 등)을 넣는 안을 04 문서에서 검토한다.
- 마지막 스테이지(NPC 동행)가 첫 스테이지보다 쉬운 편이다(SC06-2 > SC06-1 등) — 의도(합류 직전의 "함께 싸우는 체감")와 맞는다.
""")
