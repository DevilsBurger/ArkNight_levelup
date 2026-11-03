"""results_ch1.csv · sweep.csv → 08 문서 1장 표(§2.1~2.3, §3, §4)를 제자리에서 갱신한다. 서술문은 유지."""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from report import load, table_by_policy, table_by_growth, table_detail, table_tags
doc = Path(sys.argv[3]); rows = [r for r in load(sys.argv[1]) if r['stage'].startswith('1-')]; sw = load(sys.argv[2])
s = doc.read_text(encoding="utf-8")
st = ['1-1', '1-2', '1-3', '1-4', '1-5', '1-6', '1-7', '1-8']
def g(pol, grow, stage, k): return float(next(r for r in rows if r['policy'] == pol and r['growth'] == grow and r['stage'] == stage)[k])
def pc(x): return f"{x*100:.0f}%"
def mark(ok): return "✅" if ok else "❌"
tgt_D = {'1-1': .98, '1-2': .90, '1-3': .95, '1-4': .90, '1-5': .90, '1-6': .85, '1-7': .85, '1-8': .85}
tgt_B = {'1-1': .95, '1-2': .85, '1-3': .85, '1-4': .85, '1-5': .85, '1-6': .80, '1-7': .80, '1-8': .75}
tgt_Ac = {'1-1': 1.0, '1-2': .95, '1-3': .90, '1-4': .80, '1-5': .85, '1-6': .75, '1-7': .65, '1-8': .55}
tgt_As = {'1-4': (.2, .6), '1-5': (.5, .95), '1-6': (.3, .7), '1-7': (.15, .5), '1-8': (.1, .5)}
judge = ["| 스테이지 | D·G1 ★3 (목표) | B·G1 ★3 (목표) | A·G1 클리어 (목표) | A·G1 ★3 (범위) | S·G1 ★3 | G0·D 클리어 |", "| :-: | :-: | :-: | :-: | :-: | :-: | :-: |"]
for x in st:
    d = g('D', 'G1', x, 'P_star3'); b = g('B', 'G1', x, 'P_star3'); ac = g('A', 'G1', x, 'P_clear'); as_ = g('A', 'G1', x, 'P_star3'); so = g('S', 'G1', x, 'P_star3'); g0 = g('D', 'G0', x, 'P_clear')
    rng = tgt_As.get(x)
    judge.append(f"| {x} | {pc(d)} ({pc(tgt_D[x])}) {mark(d>=tgt_D[x]-0.005)} | {pc(b)} ({pc(tgt_B[x])}) {mark(b>=tgt_B[x]-0.005)} | {pc(ac)} ({pc(tgt_Ac[x])}) {mark(ac>=tgt_Ac[x]-0.005)} | {pc(as_)}" + (f" ({pc(rng[0])}~{pc(rng[1])}) {mark(rng[0]<=as_<=rng[1])}" if rng else "") + f" | {pc(so)} | {pc(g0)} {mark(g0>=0.5)} |")
# 표 블록 치환: 섹션 안의 "| 스테이지 |" 로 시작하는 n번째 표
def replace_table(text, start_heading, end_heading, n, new_table):
    i = text.index(start_heading); j = text.index(end_heading, i)
    seg = text[i:j]
    tables = list(re.finditer(r"(?ms)^\| 스테이지 \|.*?(?=\n\n|\Z)", seg))
    m = tables[n]
    seg = seg[:m.start()] + new_table + seg[m.end():]
    return text[:i] + seg + text[j:]
s = replace_table(s, "### 2.1 정책 × 스테이지", "### 2.2", 0, table_by_policy(rows, 'G1'))
s = replace_table(s, "### 2.1 정책 × 스테이지", "### 2.2", 1, table_by_policy(rows, 'G1', 'P_clear'))
s = replace_table(s, "### 2.2 성장 × 스테이지", "### 2.3", 0, table_by_growth(rows, 'D'))
s = replace_table(s, "### 2.2 성장 × 스테이지", "### 2.3", 1, table_by_growth(rows, 'B'))
s = replace_table(s, "### 2.2 성장 × 스테이지", "### 2.3", 2, table_by_growth(rows, 'A', 'P_clear'))
s = replace_table(s, "### 2.2 성장 × 스테이지", "### 2.3", 3, table_by_growth(rows, 'A'))
s = replace_table(s, "### 2.2 성장 × 스테이지", "### 2.3", 4, table_by_growth(rows, 'S'))
s = replace_table(s, "### 2.3 상세 지표", "---\n\n## 3.", 0, table_detail(rows, 'D', 'G1'))
s = replace_table(s, "### 2.3 상세 지표", "---\n\n## 3.", 1, table_detail(rows, 'A', 'G1'))
s = replace_table(s, "### 2.3 상세 지표", "---\n\n## 3.", 2, table_detail(rows, 'S', 'G1'))
s = replace_table(s, "## 3. 목표 곡선 판정", "| 보조 제약 |", 0, "\n".join(judge))
s = replace_table(s, "## 4. 민감도", "해석(난이도 레버 순위)", 0, table_tags(sw, 'D', 'G1'))
s = replace_table(s, "## 4. 민감도", "해석(난이도 레버 순위)", 1, table_tags(sw, 'D', 'G1', 'P_clear'))
doc.write_text(s, encoding="utf-8")
print("ch1 tables refreshed")
