// 코어 데이터 레코드(불변). JSON 로더는 System.Text.Json 없이 최소 파서로 — Unity netstandard2.1 호환을 위해 외부 의존 없음.
// 10 TDD §4.3. StageDef 스키마는 02 GDD §8.2 · unity/Data/Stages/*.json 과 동일.
using System.Collections.Generic;

namespace Army.Core
{
    public enum Tile : byte { Blocked, Ground, High, Path, Spawn, Defense, Sealed, Trap, Accel, Heal }
    public enum DamageType : byte { Physical, Arts, True, Heal, None }

    public static class TileCodes
    {
        public static Tile Parse(char c)
        {
            switch (c)
            {
                case 'G': return Tile.Ground; case 'H': return Tile.High; case 'P': return Tile.Path; case 'S': return Tile.Spawn;
                case 'D': return Tile.Defense; case 'L': return Tile.Sealed; case 'T': return Tile.Trap; case 'A': return Tile.Accel; case 'R': return Tile.Heal;
                default: return Tile.Blocked;
            }
        }
        public static bool Walkable(Tile t) => t != Tile.Blocked && t != Tile.High;
        public static bool GroundDeploy(Tile t) => t == Tile.Ground || t == Tile.Sealed || t == Tile.Trap || t == Tile.Accel || t == Tile.Heal;
        public static bool HeroAllowed(Tile t) => t == Tile.Ground || t == Tile.Trap || t == Tile.Accel || t == Tile.Heal;
    }

    public struct Point { public int X, Y; public Point(int x, int y) { X = x; Y = y; } public override string ToString() => "(" + X + "," + Y + ")"; }

    public sealed class WaveDef { public int TimeMilli; public string EnemyId; public string Route; public int Count; public int IntervalMilli; }

    public sealed class RouteDef
    {
        public string Id; public bool Air; public List<Point> Tiles = new List<Point>();
        public int Length => Tiles.Count - 1;
        /// <summary>웨이포인트를 축 정렬 타일 열로 전개(stagedef_loader.expand_route 와 동일 규칙).</summary>
        public static List<Point> Expand(List<Point> pts)
        {
            var tiles = new List<Point>();
            for (int i = 0; i + 1 < pts.Count; i++)
            {
                var a = pts[i]; var b = pts[i + 1];
                var seg = new List<Point>();
                if (a.X == b.X) { int step = b.Y > a.Y ? 1 : -1; for (int y = a.Y; y != b.Y + step; y += step) seg.Add(new Point(a.X, y)); }
                else { int step = b.X > a.X ? 1 : -1; for (int x = a.X; x != b.X + step; x += step) seg.Add(new Point(x, a.Y)); }
                if (tiles.Count > 0 && tiles[tiles.Count - 1].X == seg[0].X && tiles[tiles.Count - 1].Y == seg[0].Y) seg.RemoveAt(0);
                tiles.AddRange(seg);
            }
            return tiles;
        }
    }

    public sealed class NpcDef { public string Id; public string Unit; public Point Tile; public char Dir; public int Level; public string Role; }

    public sealed class StageDef
    {
        public string Id; public int Chapter; public string Name;
        public int W, H; public Tile[] Grid;            // Grid[y * W + x], y=0 이 아래
        public int Lives; public int InitialDp10;        // DP ×10 정수
        public int DpRegenPerTick10;                     // 틱당 DP×10 (0.7/s → 7/30 ≈ 0.233 → 누적은 ×1000 으로)
        public int DpRegenMilliPerSec;                   // 700 = 0.7/s
        public int DeployLimit; public Point? HeroDefault; public string HeroMode;
        public List<Point> Sealed = new List<Point>();
        public List<RouteDef> Routes = new List<RouteDef>();
        public List<WaveDef> Waves = new List<WaveDef>();
        public int ScaleHpPct = 100, ScaleAtkPct = 100, ScaleDefPct = 100;
        public List<NpcDef> Npcs = new List<NpcDef>();
        public uint Seed;
        public Tile At(int x, int y) => (x < 0 || y < 0 || x >= W || y >= H) ? Tile.Blocked : Grid[y * W + x];
    }

    public sealed class EnemyDef
    {
        public string Id; public string Kind = "normal"; public int Hp, Atk, Def, Res; public int SpeedMilli; public int Weight; public bool Flying;
        public int RangedTiles; public bool Arts; public bool Charge; public bool Stealth; public bool Revive; public int EnrageMilli = 1000; public int IntervalMilli = 1000;
        public int DpReward = 1, SpReward = 1;
    }

    public sealed class UnitDef
    {
        public string Id; public string Class; public int Rarity = 4; public int Hp, Atk, Def, Res; public int Block; public int Cost; public int RedeploySec; public int IntervalMilli;
        public string Range = "R1"; public DamageType Dmg = DamageType.Physical; public bool High;
    }

    public sealed class HeroDef
    {
        public int Hp = 3300, Atk = 800, Def = 150, Res = 10, Block = 3, IntervalMilli = 900, RangeFront = 1, MaxTargets = 5;
        public int RelocateCdMilli = 8000, RelocateTimeMilli = 400, KnockdownMilli = 10000, ReviveHpPct = 30;
        public int MomentumMax = 10, MomentumAtkPct = 3, MomentumDecayAfterMilli = 5000, MomentumDecayEveryMilli = 5000;
        public int UltSp = 20, UltAtkPct = 300, UltTiles = 5, UltStunMilli = 1000;
    }

    public sealed class Rules
    {
        public int DpCap10 = 990; public int RefundPct = 50; public int[] RedeployMultPct = { 100, 150, 200 }; public int DeathCooldownMult = 2;
        public int MinDamagePct = 5; public int NaturalSpPerSec = 1; public int HeroKillDpNormal = 1, HeroKillDpElite = 2, HeroKillDpBoss = 5;
        public int SpPerKillNormal = 1, SpPerKillElite = 2, SpPerKillBoss = 5; public int TickHz = 30;
    }
}
