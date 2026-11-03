"""results_all.csv · sweep_all.csv → 08 문서 §8 (2~5장 1차 결과) 마크다운을 stdout 으로."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from report import load, table_by_policy, table_by_growth, table_detail, table_tags
rows = load(sys.argv[1]); sw = load(sys.argv[2])
def only(rows, chs): return [r for r in rows if int(r["stage"].split("-")[0]) in chs]
R = only(rows, {2, 3, 4, 5})
def g(pol, grow, stage, k): return float(next(r for r in rows if r["policy"] == pol and r["growth"] == grow and r["stage"] == stage)[k])
stages = sorted({r["stage"] for r in R}, key=lambda s: tuple(int(v) for v in s.split("-")))
low = [s for s in stages if g("D", "G1", s, "P_star3") < 0.5]
lowc = [s for s in stages if g("D", "G1", s, "P_clear") < 0.9]
solo = [s for s in stages if g("S", "G1", s, "P_star3") > 0.2]
a_fail = [s for s in stages if g("A", "G1", s, "P_clear") < 0.5]
hk = [g("D", "G1", s, "hero_kill_share") for s in stages]
print(f"""
---

## 8. 2~5장 1차 실행 (StageDef 초안 + 2차 보정)

> 2~5장 32스테이지 StageDef를 작성(04 문서 §6)하고 같은 파이프라인을 돌렸다. 셀당 300런(95% CI ±5.7%p). 1장과 달리 **초안이 지나치게 어려운** 쪽이었고, 구조적 결함 6건을 고친 뒤 챕터 배율 강도를 0.6으로 내렸다.

### 8.1 발견과 조치
| # | 발견 | 조치 |
| :-: | :--- | :--- |
| F8 | 첫 비행 웨이브가 3초에 나와 사수를 살 DP가 없고, 박쥐(속도 1.6)가 7초 만에 도달 → 4-6이 14초 만에 패배 | 비행 속도 1.1~1.2, 첫 비행 웨이브 ≥ 20초, 비행 웨이브 간격 2~2.5s |
| F9 | 3경로 스테이지의 개막 웨이브(3 · 6 · 10초)가 DP가 모이기 전에 세 길을 연다 | 개막 간격 12s(3경로 이상) · 8s(2경로), 3경로 이상 초기 DP +3 |
| F10 | 카드 8장 코스트 ≈ 120 DP vs 초기 12 · 회복 0.7 → 1분에 3~4명 | 챕터별 초기 DP 12 / 15 / 18 / 20, 회복 0.7 / 0.75 / 0.8 / 0.85 |
| F11 | 보스 2 · 3 · 5(ATK 450~600)가 주인공을 먼저 넉다운(주인공 DEF는 성장이 거의 없음), 4-8 비행 보스는 날면서 전진해 사수만으로 40초 안에 못 잡음 | 보스 ATK 350~450, HP 하향, 비행 페이즈 제자리 선회, 보스전 주인공 기본 위치를 뒤로(방패가 앞에서 받음) + 정책도 주인공 앞 포스트 선호 |
| F12 | 스켈레톤 주술사(마법 원거리, 1초 간격)가 방패를 5초 만에 녹임 | 원거리 적 공격 간격: 일반 1.5s · 마법 2.5s (GDD §7.2) |
| F13 | 챕터 배율(초기 표)이 기본 보정(×1.5/×1.3) 위에 곱해져 4~5장은 D도 클리어 0~5% | 배율 초과분 ×0.6 (GDD §7.5 갱신) |
| F14 | 과밀 스테이지(2-4 · 2-5 · 2-7 · 3-4 · 3-6 · 3-7 · 4-2 · 4-5 · 4-6 · 4-7 · 5-2 · 5-3 · 5-7)와 제단 소환 속도 | 적 수 10~20% 감축, 제단 소환물 속도 1.2, 박쥐 군단 HP 800 |
| F15 | 정책 결함 3건 — 비행 경로를 "저지 없는 경로"로 보고 DP를 영원히 아낌(4장 전멸), 주인공이 곧 적이 올 자기 경로를 비움(3-5), 추가 저지를 주인공 뒤에 둠(보스) | 수정. 수정 후 1장에서 솔로가 1-6 · 1-7을 "임박 누수 때마다 왕복"으로 ★3 → 두 경로 웨이브를 같은 시각으로 겹쳐 차단(규칙 R1 보강) |

### 8.2 정책 × 스테이지 — 성장 G1

P_★3
{table_by_policy(R, "G1")}

P_clear
{table_by_policy(R, "G1", "P_clear")}

### 8.3 성장 × 스테이지

D(균형) P_★3
{table_by_growth(R, "D")}

A(초보) P_clear
{table_by_growth(R, "A", "P_clear")}

### 8.4 상세 (D · G1)
{table_detail(R, "D", "G1")}

### 8.5 민감도 (D · G1, 2~5장) — P_★3
{table_tags(sw, "D", "G1")}

### 8.6 판정
- **D · G1 ★3 < 50%**: {", ".join(low) if low else "없음"} ({len(low)}/32) — 2차 보정 대상.
- **D · G1 클리어 < 90%**: {", ".join(lowc) if lowc else "없음"}.
- **솔로(S · G1) ★3 > 20%**: {", ".join(solo) if solo else "없음"} — NPC 동행 스테이지(2-2 · 2-5 · 3-3 · 3-6 · 4-3 · 4-6 · 5-4)는 제외하고 판정.
- **초보(A · G1) 클리어 < 50%**: {", ".join(a_fail) if a_fail else "없음"} — 2~5장은 1장보다 초보 격차가 크다. 숨은 합류 · 성장(G2)으로 좁혀지는지 §8.3 참조.
- **군단 기여(주인공 처치 비율, D · G1)**: {min(hk)*100:.0f}~{max(hk)*100:.0f}%. 4장 이후 20~40%로 내려간다 — 비행 · 은신 · 마법 등 주인공이 못 잡는 적이 늘어나는 설계 의도와 일치. 다만 30% 아래면 "주인공이 강하다"는 체감이 약해질 수 있어 주인공 범위 공격의 후반 성장(무쌍 트리)을 재검토한다.

### 8.7 2차 보정 계획 (2~5장)
1. ★3 < 50% 스테이지는 레인별 누수 로그(`leak_log`)로 어느 길이 새는지 확인하고 웨이브 단위로 조정한다. 공통 후보: 3경로 + 은신/마법 혼합(2-4 · 3-6), 비행 + 지상 혼합(4-5 · 4-7), 봉인 회랑(5-2), 제단(5-3).
2. 4-8(비행 보스): 선회 중 사수 화력이 부족하면 비행 페이즈 HP 비율을 66/33 → 75/40으로 좁히거나 착지 구간을 늘린다.
3. 성장 곡선: G0(하한)에서 보스 클리어 ≥ 30%가 되는지 확인하고, 안 되면 챕터 보스 권장 레벨을 맵 정보에 노출한다.
4. 모델 보강: 분신 식별(B03), 보스 강타, 중량 · 밀치기, 잠재 · 유대 · 장비.
""")
