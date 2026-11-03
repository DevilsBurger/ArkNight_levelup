# core — 결정론 전투 코어 스캐폴딩 (Army.Core)

10 TDD §3 · §4 · §12. **컴파일 미검증**: 작성 환경에 dotnet 이 없었다. 로컬에서 먼저 확인한다.

```bash
dotnet test core            # 저장소 루트에서. unity/Data 의 StageDef · Enemies.json 을 읽는다
```

| 파일 | 내용 | 상태 |
| :--- | :--- | :--- |
| `Army.Core/Fixed32.cs` | 1/1000 고정소수점, XorShift32 | 완성 |
| `Army.Core/Data.cs` | Tile · StageDef · RouteDef · EnemyDef · UnitDef · HeroDef · Rules | 완성(UnitDef 는 params.yaml → JSON 내보내기 전까지 테스트에서 수동 생성) |
| `Army.Core/Json.cs` | 의존성 없는 최소 JSON 파서, StageLoader · EnemyLoader | 완성 |
| `Army.Core/Commands.cs` | Command · InputLog | 완성 |
| `Army.Core/BattleSim.cs` | 틱 루프: 스폰 · 이동 · 저지 · 이산 타격 · 자원 · 넉다운 · 이탈 · 승패 · 상태 해시 | 골격. TODO: 스킬 · 권능 · 치유 · 보스 페이즈 · 특수 타일 · 각성 전 주인공 · 비행 표적 규칙 세부 |
| `Army.Core.Tests/CoreTests.cs` | 고정소수점 · 난수 재현 · 1-1 로드 · 같은 입력 같은 해시 · 1-1 클리어 | 작성 |

다음: `tools/export_core_data.py`(params.yaml → UnitDefs.json · HeroDef.json · Rules.json), 헤드리스 러너, 파이썬 등가 모델과 1-1~1-3 결과 비교(10 TDD §11 1~2주).
