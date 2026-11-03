# mermaid_check — 문서 다이어그램 검증 · 렌더링

```bash
cd tools/mermaid_check
npm install            # mermaid + playwright (처음 한 번: npx playwright install chromium)
node validate.js ../../docs/03_게임_흐름_구조_다이어그램.md
node render_all.js ../../docs/03_게임_흐름_구조_다이어그램.md out/diagram 2
```

- `validate.js <md>`: 모든 ```mermaid 블록을 파싱 · 렌더링해 실패한 블록 번호와 오류를 출력한다. 실패가 있으면 종료 코드 1.
- `render_all.js <md> <출력 접두사> [배율]`: 블록마다 PNG를 저장한다(기본 배율 2).
- GitHub가 쓰는 Mermaid 버전과 큰 차이가 없도록 `mermaid` 버전은 고정한다.
