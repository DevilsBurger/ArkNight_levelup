// 결정론 전투 코어 — 틱 루프 골격. 10 TDD §4.2. 파이썬 등가 모델(tools/difficulty_sim/model.py)과 같은 규칙을 "이산 타격 · 고정소수점" 으로 구현한다.
// 이 파일은 스캐폴딩이다: 이동 · 저지 · 공격 · 자원 · 승패 · 해시는 동작하지만 스킬 · 보스 페이즈 · 특수 타일 · 권능은 TODO 로 표시했다.
using System;
using System.Collections.Generic;

namespace Army.Core
{
    public enum EndState : byte { Running, Cleared, FailedLeak, FailedBoss }

    public sealed class Enemy
    {
        public int Id; public EnemyDef Def; public RouteDef Route; public Fixed32 P; public int Hp; public int MaxHp; public int Atk, Dfn, Res;
        public Unit BlockedBy; public int StunUntilTick; public bool ChargePending; public bool Alive = true; public int NextAttackTick;
    }

    public enum UnitKind : byte { Hero, Legion, Npc, Civilian }

    public sealed class Unit
    {
        public int Id; public string DefId; public UnitKind Kind; public UnitDef Def; public Point Tile; public char Dir;
        public int Hp, MaxHp, Atk, Dfn, Res, Block; public bool High; public readonly List<Enemy> Blocked = new List<Enemy>();
        public bool Alive = true; public int KnockdownUntilTick; public int MovingUntilTick; public int CooldownUntilTick; public int NextAttackTick;
        public int Momentum; public int LastKillTick = -100000; public int UltSp10;
        public readonly Dictionary<string, int> LaneIndex = new Dictionary<string, int>();     // 지상: 레인 → 인덱스
        public readonly Dictionary<string, HashSet<int>> Coverage = new Dictionary<string, HashSet<int>>(); // 고지대: 레인 → 인덱스 집합
        public bool Active(int tick) => Alive && KnockdownUntilTick <= tick && MovingUntilTick <= tick;
        public int FreeSlots => Block - Blocked.Count;
    }

    public sealed class Card { public UnitDef Def; public int DeployCount; public int CooldownUntilTick; public Unit Unit; }

    public sealed class BattleResult
    {
        public EndState End; public int Lives; public int Leaks; public int Knockdowns; public int Kills; public int HeroKills; public int Ticks; public ulong Hash;
        public bool Star3 => End == EndState.Cleared && Leaks == 0 && Knockdowns == 0;
    }

    public sealed class BattleSim
    {
        public readonly StageDef Stage; public readonly Rules Rules; public readonly HeroDef HeroDef;
        private readonly Dictionary<string, EnemyDef> _enemies; private readonly Dictionary<string, UnitDef> _units;
        private readonly XorShift32 _rng;
        public int Tick { get; private set; }
        public int Dp10 { get; private set; }                 // DP × 10
        private long _dpAccMilli;                            // 자연 회복 누적 (DP × 1000)
        public int Lives { get; private set; }
        public readonly List<Enemy> Enemies = new List<Enemy>();
        public readonly List<Unit> Units = new List<Unit>();
        public readonly List<Card> Cards = new List<Card>();
        public Unit Hero { get; private set; }
        public readonly BattleResult Result = new BattleResult();
        private int _spawnIndex; private readonly List<(int tick, string enemy, string route)> _spawnQueue = new List<(int, string, string)>();
        private int _nextId = 1; private readonly Dictionary<(int, int), Unit> _occupied = new Dictionary<(int, int), Unit>();
        private readonly HashSet<(int, int)> _sealed = new HashSet<(int, int)>();
        public EndState End { get; private set; } = EndState.Running;
        private readonly Dictionary<string, RouteDef> _routes = new Dictionary<string, RouteDef>();
        public readonly List<ulong> CheckpointHashes = new List<ulong>();

        public BattleSim(StageDef stage, Dictionary<string, EnemyDef> enemies, Dictionary<string, UnitDef> units, IEnumerable<UnitDef> squad, HeroDef heroDef, Rules rules, uint seed)
        {
            Stage = stage; _enemies = enemies; _units = units; HeroDef = heroDef; Rules = rules; _rng = new XorShift32(seed ^ stage.Seed);
            Lives = stage.Lives; Dp10 = stage.InitialDp10;
            foreach (var r in stage.Routes) _routes[r.Id] = r;
            foreach (var w in stage.Waves) for (int k = 0; k < w.Count; k++) _spawnQueue.Add(((w.TimeMilli + k * w.IntervalMilli) * rules.TickHz / 1000, w.EnemyId, w.Route));
            _spawnQueue.Sort((a, b) => a.tick != b.tick ? a.tick.CompareTo(b.tick) : string.CompareOrdinal(a.enemy, b.enemy));
            foreach (var p in stage.Sealed) _sealed.Add((p.X, p.Y));
            foreach (var u in squad) Cards.Add(new Card { Def = u });
            // 주인공 (각성 후 기준). 각성 전 모드는 TODO.
            Hero = new Unit { Id = _nextId++, DefId = "HERO", Kind = UnitKind.Hero, Hp = heroDef.Hp, MaxHp = heroDef.Hp, Atk = heroDef.Atk, Dfn = heroDef.Def, Res = heroDef.Res, Block = heroDef.Block };
            if (stage.HeroDefault.HasValue) PlaceGround(Hero, stage.HeroDefault.Value, 'E');
            // NPC
            foreach (var n in stage.Npcs)
            {
                UnitDef ud; if (!units.TryGetValue(n.Unit, out ud)) continue;
                var u = MakeUnit(ud, n.Unit == "CIVILIAN" ? UnitKind.Civilian : UnitKind.Npc); Place(u, n.Tile, n.Dir);
            }
        }

        // ------------------------------------------------------------------ 배치
        private Unit MakeUnit(UnitDef d, UnitKind kind) => new Unit { Id = _nextId++, DefId = d.Id, Kind = kind, Def = d, Hp = d.Hp, MaxHp = d.Hp, Atk = d.Atk, Dfn = d.Def, Res = d.Res, Block = d.Block, High = d.High };

        private void Place(Unit u, Point tile, char dir)
        {
            if (u.High) PlaceHigh(u, tile, dir); else PlaceGround(u, tile, dir);
        }

        private void PlaceGround(Unit u, Point tile, char dir)
        {
            u.Tile = tile; u.Dir = dir; _occupied[(tile.X, tile.Y)] = u; if (!Units.Contains(u)) Units.Add(u);
            u.LaneIndex.Clear();
            foreach (var r in Stage.Routes) { if (r.Air) continue; int idx = r.Tiles.FindIndex(t => t.X == tile.X && t.Y == tile.Y); if (idx >= 0) u.LaneIndex[r.Id] = idx; }
            // 타일 위에 서 있던 적을 저지
            foreach (var e in Enemies)
            {
                int idx; if (!e.Alive || e.BlockedBy != null || e.Def.Flying || !u.LaneIndex.TryGetValue(e.Route.Id, out idx)) continue;
                if (e.P.Floor == idx && u.FreeSlots > 0 && u.Block > 0) { e.BlockedBy = u; u.Blocked.Add(e); e.P = Fixed32.FromInt(idx); }
            }
        }

        private void PlaceHigh(Unit u, Point tile, char dir)
        {
            u.Tile = tile; u.Dir = dir; _occupied[(tile.X, tile.Y)] = u; if (!Units.Contains(u)) Units.Add(u);
            u.Coverage.Clear();
            foreach (var off in RangeTemplates.Get(u.Def.Range))
            {
                var r = RangeTemplates.Rotate(off, dir); var t = new Point(tile.X + r.X, tile.Y + r.Y);
                foreach (var route in Stage.Routes)
                {
                    int idx = route.Tiles.FindIndex(p => p.X == t.X && p.Y == t.Y);
                    if (idx >= 0) { HashSet<int> set; if (!u.Coverage.TryGetValue(route.Id, out set)) u.Coverage[route.Id] = set = new HashSet<int>(); set.Add(idx); }
                }
            }
        }

        public bool TryDeploy(Card card, Point tile, char dir)
        {
            if (card.Unit != null || card.CooldownUntilTick > Tick) return false;
            int cost10 = CurrentCost(card) * 10; if (Dp10 < cost10) return false;
            if (_occupied.ContainsKey((tile.X, tile.Y))) return false;
            var t = Stage.At(tile.X, tile.Y);
            if (card.Def.High ? t != Tile.High : !TileCodes.GroundDeploy(t)) return false;
            if (DeployedLegion() >= Stage.DeployLimit) return false;
            var u = MakeUnit(card.Def, UnitKind.Legion); card.Unit = u; card.DeployCount++; Dp10 -= cost10;
            u.MovingUntilTick = Tick + (500 * Rules.TickHz / 1000); // 등장 0.5s
            Place(u, tile, dir); return true;
        }

        public int CurrentCost(Card card) { int i = Math.Min(card.DeployCount, Rules.RedeployMultPct.Length - 1); return Math.Min(99, Fixed32.Percent(card.Def.Cost, Rules.RedeployMultPct[i])); }
        public int DeployedLegion() { int n = 0; foreach (var u in Units) if (u.Kind == UnitKind.Legion && u.Alive) n++; return n; }

        public void Retreat(Card card)
        {
            var u = card.Unit; if (u == null || !u.Alive) return;
            int prev = Math.Min(99, Fixed32.Percent(card.Def.Cost, Rules.RedeployMultPct[Math.Min(card.DeployCount - 1, Rules.RedeployMultPct.Length - 1)]));
            Dp10 = Math.Min(Rules.DpCap10, Dp10 + Fixed32.Percent(prev, Rules.RefundPct) * 10);
            RemoveUnit(u); card.Unit = null; card.CooldownUntilTick = Tick + card.Def.RedeploySec * Rules.TickHz;
        }

        private void RemoveUnit(Unit u)
        {
            foreach (var e in u.Blocked) e.BlockedBy = null; u.Blocked.Clear(); u.Alive = false; _occupied.Remove((u.Tile.X, u.Tile.Y)); Units.Remove(u);
        }

        public bool TryHeroMove(Point tile)
        {
            var h = Hero; if (!h.Active(Tick) || h.CooldownUntilTick > Tick) return false;
            var t = Stage.At(tile.X, tile.Y); if (!TileCodes.HeroAllowed(t) || _sealed.Contains((tile.X, tile.Y)) || _occupied.ContainsKey((tile.X, tile.Y))) return false;
            foreach (var e in h.Blocked) e.BlockedBy = null; h.Blocked.Clear(); _occupied.Remove((h.Tile.X, h.Tile.Y));
            PlaceGround(h, tile, 'E');
            h.MovingUntilTick = Tick + HeroDef.RelocateTimeMilli * Rules.TickHz / 1000; h.CooldownUntilTick = Tick + HeroDef.RelocateCdMilli * Rules.TickHz / 1000;
            return true;
        }

        // ------------------------------------------------------------------ 틱
        public void Apply(Command c)
        {
            switch (c.Type)
            {
                case CommandType.HeroPlace: if (Tick == 0 && !_occupied.ContainsKey((c.X, c.Y)) && TileCodes.HeroAllowed(Stage.At(c.X, c.Y))) { _occupied.Remove((Hero.Tile.X, Hero.Tile.Y)); PlaceGround(Hero, new Point(c.X, c.Y), 'E'); } break;
                case CommandType.Deploy: { var card = Cards.Find(k => k.Def.Id == c.Unit); if (card != null) TryDeploy(card, new Point(c.X, c.Y), c.Dir); break; }
                case CommandType.Retreat: { var card = Cards.Find(k => k.Def.Id == c.Unit); if (card != null) Retreat(card); break; }
                case CommandType.HeroMove: TryHeroMove(new Point(c.X, c.Y)); break;
                case CommandType.Skill: /* TODO 스킬 */ break;
                case CommandType.Ult: /* TODO 권능 일섬 */ break;
            }
        }

        public void Step(List<Command> cmdsThisTick)
        {
            if (End != EndState.Running) return;
            if (cmdsThisTick != null) foreach (var c in cmdsThisTick) Apply(c);
            // 자원: DP 자연 회복 (×1000 누적 → ×10 로 환산)
            _dpAccMilli += Stage.DpRegenMilliPerSec; // per tick: milli/sec ÷ Hz → 누적은 Hz 로 나눈 몫만 반영
            while (_dpAccMilli >= 100 * Rules.TickHz) { _dpAccMilli -= 100 * Rules.TickHz; Dp10 = Math.Min(Rules.DpCap10, Dp10 + 1); }
            Spawn(); Move(); Attacks(); Timers();
            Tick++;
            if (Tick % (10 * Rules.TickHz) == 0) CheckpointHashes.Add(StateHash.Compute(this));
            CheckEnd();
        }

        private void Spawn()
        {
            while (_spawnIndex < _spawnQueue.Count && _spawnQueue[_spawnIndex].tick <= Tick)
            {
                var s = _spawnQueue[_spawnIndex++]; EnemyDef d; if (!_enemies.TryGetValue(s.enemy, out d)) continue;
                var e = new Enemy { Id = _nextId++, Def = d, Route = _routes[s.route], P = Fixed32.Zero, ChargePending = d.Charge, NextAttackTick = Tick };
                bool boss = d.Kind == "boss";
                e.MaxHp = e.Hp = boss ? d.Hp : Fixed32.Percent(d.Hp, Stage.ScaleHpPct);
                e.Atk = boss ? d.Atk : Fixed32.Percent(d.Atk, Stage.ScaleAtkPct); e.Dfn = boss ? d.Def : Fixed32.Percent(d.Def, Stage.ScaleDefPct); e.Res = d.Res;
                Enemies.Add(e);
            }
        }

        private void Move()
        {
            int L;
            foreach (var e in Enemies)
            {
                if (!e.Alive || e.StunUntilTick > Tick || e.BlockedBy != null) continue;
                var prev = e.P;
                int speedMilli = e.Def.SpeedMilli; if (e.Def.Kind == "boss") speedMilli = (int)((long)speedMilli * e.Def.EnrageMilli / 1000);
                e.P = e.P + Fixed32.FromMilli(speedMilli / Rules.TickHz);
                L = e.Route.Length;
                if (!e.Def.Flying && !e.Route.Air)
                {
                    // 저지: prev < idx ≤ P 인 지상 아군(ID 순) 중 빈 슬롯
                    Unit best = null; int bestIdx = int.MaxValue;
                    foreach (var u in Units)
                    {
                        int idx; if (!u.Alive || !u.Active(Tick) || u.High || u.Block <= 0 || u.Kind == UnitKind.Civilian || !u.LaneIndex.TryGetValue(e.Route.Id, out idx)) continue;
                        if (prev < Fixed32.FromInt(idx) && Fixed32.FromInt(idx) <= e.P && u.FreeSlots > 0 && idx < bestIdx) { best = u; bestIdx = idx; }
                    }
                    if (best != null) { e.BlockedBy = best; best.Blocked.Add(e); e.P = Fixed32.FromInt(bestIdx); continue; }
                }
                if (e.P >= Fixed32.FromInt(L))
                {
                    e.Alive = false; Result.Leaks++;
                    if (e.Def.Kind == "boss") { Lives = 0; End = EndState.FailedBoss; } else Lives--;
                }
            }
        }

        private static int Damage(int atk, bool arts, int def, int res, int minPct)
        {
            int raw = arts ? Fixed32.Percent(atk, 100 - res) : atk - def;
            return Math.Max(raw, Fixed32.Percent(atk, minPct));
        }

        private void Attacks()
        {
            // 아군 (ID 순). 이산 타격: NextAttackTick 도달 시 1회
            foreach (var u in Units)
            {
                if (!u.Active(Tick) || u.Kind == UnitKind.Civilian || u.NextAttackTick > Tick) continue;
                if (u.Kind == UnitKind.Hero) { HeroAttack(u); continue; }
                if (u.Def.Dmg == DamageType.Heal) { /* TODO 치유 */ u.NextAttackTick = Tick + u.Def.IntervalMilli * Rules.TickHz / 1000; continue; }
                Enemy target = null;
                if (!u.High)
                {
                    if (u.Blocked.Count > 0) target = u.Blocked[0];
                    else foreach (var e in Enemies) { int idx; if (e.Alive && e.BlockedBy == null && !e.Def.Flying && u.LaneIndex.TryGetValue(e.Route.Id, out idx) && e.P >= Fixed32.FromInt(idx - 1) && e.P < Fixed32.FromInt(idx + 1)) { if (target == null || e.P > target.P) target = e; } }
                }
                else
                {
                    foreach (var e in Enemies) { HashSet<int> set; if (e.Alive && u.Coverage.TryGetValue(e.Route.Id, out set) && set.Contains(e.P.Floor) && !(e.Def.Stealth && e.BlockedBy == null)) { if (target == null || e.P > target.P) target = e; } }
                }
                if (target == null) continue;
                Hit(target, Damage(u.Atk, u.Def.Dmg == DamageType.Arts, target.Dfn, target.Res, Rules.MinDamagePct), u);
                u.NextAttackTick = Tick + u.Def.IntervalMilli * Rules.TickHz / 1000;
            }
            // 적
            foreach (var e in Enemies)
            {
                if (!e.Alive || e.StunUntilTick > Tick || e.NextAttackTick > Tick) continue;
                Unit target = e.BlockedBy;
                if (target == null && e.Def.RangedTiles > 0)
                {
                    int bestD = int.MaxValue;
                    foreach (var u in Units) { int idx; if (!u.Alive || u.KnockdownUntilTick > Tick || u.High || u.Kind == UnitKind.Civilian || !u.LaneIndex.TryGetValue(e.Route.Id, out idx)) continue; int d = idx - e.P.Floor; if (d >= 0 && d <= e.Def.RangedTiles && d < bestD) { bestD = d; target = u; } }
                }
                if (target == null) continue;
                int dmg = Damage(e.Atk, e.Def.Arts, target.Dfn, target.Res, Rules.MinDamagePct);
                if (e.ChargePending && e.BlockedBy == target) { dmg *= 2; e.ChargePending = false; }
                HitUnit(target, dmg);
                e.NextAttackTick = Tick + e.Def.IntervalMilli * Rules.TickHz / 1000;
            }
        }

        private void HeroAttack(Unit h)
        {
            var targets = new List<Enemy>();
            foreach (var e in Enemies)
            {
                int idx; if (!e.Alive || e.Def.Flying || !h.LaneIndex.TryGetValue(e.Route.Id, out idx)) continue;
                if (e.P >= Fixed32.FromInt(idx - HeroDef.RangeFront) && e.P < Fixed32.FromInt(idx + 1)) targets.Add(e);
            }
            if (targets.Count == 0) return;
            targets.Sort((a, b) => { int ba = a.BlockedBy == h ? 0 : 1, bb = b.BlockedBy == h ? 0 : 1; if (ba != bb) return ba.CompareTo(bb); if (a.P.Raw != b.P.Raw) return b.P.Raw.CompareTo(a.P.Raw); return a.Id.CompareTo(b.Id); });
            int atk = Fixed32.Percent(h.Atk, 100 + HeroDef.MomentumAtkPct * h.Momentum);
            for (int i = 0; i < targets.Count && i < HeroDef.MaxTargets; i++) Hit(targets[i], Damage(atk, false, targets[i].Dfn, targets[i].Res, Rules.MinDamagePct), h);
            int interval = Fixed32.Percent(HeroDef.IntervalMilli, 100 - HeroDef.MomentumAtkPct * h.Momentum);
            h.NextAttackTick = Tick + Math.Max(200, interval) * Rules.TickHz / 1000;
        }

        private void Hit(Enemy e, int dmg, Unit src)
        {
            if (!e.Alive) return; e.Hp -= dmg;
            if (e.Hp > 0) return;
            if (e.Def.Revive) { e.Def = CloneNoRevive(e.Def); e.Hp = e.MaxHp / 2; return; }
            e.Alive = false; if (e.BlockedBy != null) e.BlockedBy.Blocked.Remove(e); e.BlockedBy = null;
            Result.Kills++;
            int sp = e.Def.Kind == "boss" ? Rules.SpPerKillBoss : e.Def.Kind == "elite" ? Rules.SpPerKillElite : Rules.SpPerKillNormal;
            Hero.UltSp10 += sp * 10;
            if (src == Hero)
            {
                Result.HeroKills++;
                int dp = e.Def.Kind == "boss" ? Rules.HeroKillDpBoss : e.Def.Kind == "elite" ? Rules.HeroKillDpElite : Rules.HeroKillDpNormal;
                Dp10 = Math.Min(Rules.DpCap10, Dp10 + dp * 10);
                Hero.Momentum = Math.Min(HeroDef.MomentumMax, Hero.Momentum + 1); Hero.LastKillTick = Tick;
            }
        }

        private static EnemyDef CloneNoRevive(EnemyDef d) => new EnemyDef { Id = d.Id, Kind = d.Kind, Hp = d.Hp, Atk = d.Atk, Def = d.Def, Res = d.Res, SpeedMilli = d.SpeedMilli, Weight = d.Weight, Flying = d.Flying, RangedTiles = d.RangedTiles, Arts = d.Arts, Charge = d.Charge, Stealth = d.Stealth, Revive = false, EnrageMilli = d.EnrageMilli, IntervalMilli = d.IntervalMilli, DpReward = d.DpReward, SpReward = d.SpReward };

        private void HitUnit(Unit u, int dmg)
        {
            if (!u.Alive || u.KnockdownUntilTick > Tick) return; u.Hp -= dmg; if (u.Hp > 0) return;
            foreach (var e in u.Blocked) e.BlockedBy = null; u.Blocked.Clear();
            if (u.Kind == UnitKind.Hero) { u.KnockdownUntilTick = Tick + HeroDef.KnockdownMilli * Rules.TickHz / 1000; u.Momentum = 0; Result.Knockdowns++; }
            else if (u.Kind == UnitKind.Npc) { u.KnockdownUntilTick = Tick + 10 * Rules.TickHz; }
            else if (u.Kind == UnitKind.Civilian) { u.Alive = false; _occupied.Remove((u.Tile.X, u.Tile.Y)); }
            else
            {
                var card = Cards.Find(c => c.Unit == u); RemoveUnit(u);
                if (card != null) { card.Unit = null; card.CooldownUntilTick = Tick + card.Def.RedeploySec * Rules.TickHz * Rules.DeathCooldownMult; }
            }
        }

        private void Timers()
        {
            var h = Hero;
            if (h.KnockdownUntilTick == Tick) { h.Hp = Fixed32.Percent(h.MaxHp, HeroDef.ReviveHpPct); h.CooldownUntilTick = Tick; }
            foreach (var u in Units) if (u.Kind == UnitKind.Npc && u.KnockdownUntilTick == Tick) u.Hp = Fixed32.Percent(u.MaxHp, 30);
            if (h.Momentum > 0 && Tick - h.LastKillTick >= HeroDef.MomentumDecayAfterMilli * Rules.TickHz / 1000) { h.Momentum--; h.LastKillTick = Tick - (HeroDef.MomentumDecayAfterMilli - HeroDef.MomentumDecayEveryMilli) * Rules.TickHz / 1000; }
            Enemies.RemoveAll(e => !e.Alive);
        }

        private void CheckEnd()
        {
            if (End != EndState.Running) { Finish(); return; }
            if (Lives <= 0) { End = EndState.FailedLeak; Finish(); return; }
            if (_spawnIndex >= _spawnQueue.Count && Enemies.Count == 0) { End = EndState.Cleared; Finish(); }
        }

        private void Finish() { Result.End = End; Result.Lives = Math.Max(0, Lives); Result.Ticks = Tick; Result.Hash = StateHash.Compute(this); }
    }

    public static class RangeTemplates
    {
        private static readonly Dictionary<string, Point[]> T = new Dictionary<string, Point[]>
        {
            { "R0", new Point[0] },
            { "R1", new[] { new Point(0, 0), new Point(1, 0) } },
            { "R3", new[] { new Point(1, -1), new Point(2, -1), new Point(1, 0), new Point(2, 0), new Point(3, 0), new Point(1, 1), new Point(2, 1) } },
            { "R3p", new[] { new Point(1, -1), new Point(2, -1), new Point(3, -1), new Point(1, 0), new Point(2, 0), new Point(3, 0), new Point(4, 0), new Point(1, 1), new Point(2, 1), new Point(3, 1) } },
            { "R4", new[] { new Point(-1, -1), new Point(0, -1), new Point(1, -1), new Point(-1, 0), new Point(0, 0), new Point(1, 0), new Point(2, 0), new Point(-1, 1), new Point(0, 1), new Point(1, 1) } },
        };
        public static Point[] Get(string id) { Point[] p; return T.TryGetValue(id, out p) ? p : T["R1"]; }
        /// <summary>템플릿은 E 가 전방. (dx 전방, dy 좌측)</summary>
        public static Point Rotate(Point o, char facing)
        {
            switch (facing) { case 'W': return new Point(-o.X, -o.Y); case 'N': return new Point(-o.Y, o.X); case 'S': return new Point(o.Y, -o.X); default: return o; }
        }
    }

    /// <summary>FNV-1a 64 상태 해시. 틱 · DP · 생명 · 유닛 · 적 상태를 ID 순으로 섞는다.</summary>
    public static class StateHash
    {
        private const ulong Offset = 14695981039346656037UL, Prime = 1099511628211UL;
        private static ulong Mix(ulong h, long v) { for (int i = 0; i < 8; i++) { h ^= (byte)(v >> (i * 8)); h *= Prime; } return h; }
        public static ulong Compute(BattleSim s)
        {
            ulong h = Offset; h = Mix(h, s.Tick); h = Mix(h, s.Dp10); h = Mix(h, s.Lives);
            var units = new List<Unit>(s.Units); units.Sort((a, b) => a.Id.CompareTo(b.Id));
            foreach (var u in units) { h = Mix(h, u.Id); h = Mix(h, u.Hp); h = Mix(h, u.Tile.X * 100 + u.Tile.Y); h = Mix(h, u.Blocked.Count); h = Mix(h, u.KnockdownUntilTick); }
            var enemies = new List<Enemy>(s.Enemies); enemies.Sort((a, b) => a.Id.CompareTo(b.Id));
            foreach (var e in enemies) { h = Mix(h, e.Id); h = Mix(h, e.Hp); h = Mix(h, e.P.Raw); h = Mix(h, e.BlockedBy == null ? 0 : e.BlockedBy.Id); }
            return h;
        }
    }
}
