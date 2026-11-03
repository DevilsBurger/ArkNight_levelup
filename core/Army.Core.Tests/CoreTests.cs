// 결정론 코어 테스트의 출발점. 실행: dotnet test core  (저장소 루트에서; unity/Data 를 상대 경로로 읽는다)
using System.Collections.Generic;
using System.IO;
using NUnit.Framework;
using Army.Core;

namespace Army.Core.Tests
{
    public class CoreTests
    {
        private static string Root()
        {
            var dir = TestContext.CurrentContext.TestDirectory;
            for (int i = 0; i < 8 && dir != null; i++) { if (Directory.Exists(Path.Combine(dir, "unity", "Data"))) return dir; dir = Path.GetDirectoryName(dir); }
            Assert.Fail("unity/Data not found"); return null;
        }

        private static Dictionary<string, UnitDef> SampleUnits()
        {
            return new Dictionary<string, UnitDef>
            {
                { "DSP_SPEAR", new UnitDef { Id = "DSP_SPEAR", Class = "spear", Rarity = 3, Hp = 1181, Atk = 408, Def = 161, Res = 0, Block = 2, Cost = 12, RedeploySec = 70, IntervalMilli = 1000, Range = "R1", Dmg = DamageType.Physical } },
                { "DSP_SNIPER", new UnitDef { Id = "DSP_SNIPER", Class = "sniper", Rarity = 3, Hp = 752, Atk = 322, Def = 97, Res = 0, Block = 1, Cost = 10, RedeploySec = 70, IntervalMilli = 1000, Range = "R3", Dmg = DamageType.Physical, High = true } },
                { "L_SHIELD_MUJIN", new UnitDef { Id = "L_SHIELD_MUJIN", Class = "shield", Rarity = 4, Hp = 1905, Atk = 279, Def = 356, Res = 10, Block = 3, Cost = 16, RedeploySec = 70, IntervalMilli = 1200, Range = "R1", Dmg = DamageType.Physical } },
                { "L_SPEAR_DOKYUNG", new UnitDef { Id = "L_SPEAR_DOKYUNG", Class = "spear", Rarity = 3, Hp = 1130, Atk = 390, Def = 154, Res = 0, Block = 2, Cost = 12, RedeploySec = 70, IntervalMilli = 1000, Range = "R1", Dmg = DamageType.Physical } },
            };
        }

        [Test]
        public void FixedPointArithmetic()
        {
            var a = Fixed32.FromMilli(1500); var b = Fixed32.FromMilli(2000);
            Assert.AreEqual(3500, (a + b).Raw); Assert.AreEqual(3000, (a * b).Raw); Assert.AreEqual(750, (a / b).Raw);
            Assert.AreEqual(1, a.Floor); Assert.AreEqual(-2, Fixed32.FromMilli(-1500).Floor);
            Assert.AreEqual(33, Fixed32.Percent(100, 33)); Assert.AreEqual(40, Fixed32.Percent(800, 5));
        }

        [Test]
        public void RandomIsReproducible()
        {
            var a = new XorShift32(12345); var b = new XorShift32(12345);
            for (int i = 0; i < 1000; i++) Assert.AreEqual(a.Next(), b.Next());
        }

        [Test]
        public void LoadsStage11AndEnemies()
        {
            string root = Root();
            var sd = StageLoader.FromJson(File.ReadAllText(Path.Combine(root, "unity", "Data", "Stages", "Stage_1-1.json")));
            Assert.AreEqual("1-1", sd.Id); Assert.AreEqual(13, sd.W); Assert.AreEqual(8, sd.H); Assert.AreEqual(8, SumCount(sd));
            Assert.AreEqual(Tile.Spawn, sd.At(0, 3)); Assert.AreEqual(Tile.Defense, sd.At(12, 3)); Assert.AreEqual(12, sd.Routes[0].Length);
            var enemies = EnemyLoader.FromJson(File.ReadAllText(Path.Combine(root, "unity", "Data", "Enemies.json")));
            Assert.AreEqual(1350, enemies["E01"].Hp); Assert.AreEqual(2700, enemies["E01_elite"].Hp); Assert.AreEqual("boss", enemies["B01"].Kind); Assert.AreEqual(2000, enemies["B01"].EnrageMilli);
        }

        private static int SumCount(StageDef sd) { int n = 0; foreach (var w in sd.Waves) n += w.Count; return n; }

        [Test]
        public void SameInputsSameHash()
        {
            string root = Root();
            var sd = StageLoader.FromJson(File.ReadAllText(Path.Combine(root, "unity", "Data", "Stages", "Stage_1-3.json")));
            var enemies = EnemyLoader.FromJson(File.ReadAllText(Path.Combine(root, "unity", "Data", "Enemies.json")));
            var hashes = new ulong[2];
            for (int run = 0; run < 2; run++)
            {
                var sim = new BattleSim(sd, enemies, SampleUnits(), new List<UnitDef>(), new HeroDef(), new Rules(), 7);
                for (int t = 0; t < 30 * 120; t++)
                {
                    var cmds = new List<Command>();
                    if (t == 30 * 28) cmds.Add(Command.HeroMove(t, 9, 1));   // B 경로로 재배치
                    if (t == 30 * 52) cmds.Add(Command.HeroMove(t, 9, 5));
                    sim.Step(cmds); if (sim.End != EndState.Running) break;
                }
                hashes[run] = sim.Result.Hash;
                Assert.AreNotEqual(EndState.Running, sim.End);
            }
            Assert.AreEqual(hashes[0], hashes[1]);
        }

        [Test]
        public void HeroAloneClearsStage11WithDispatch()
        {
            string root = Root();
            var sd = StageLoader.FromJson(File.ReadAllText(Path.Combine(root, "unity", "Data", "Stages", "Stage_1-1.json")));
            var enemies = EnemyLoader.FromJson(File.ReadAllText(Path.Combine(root, "unity", "Data", "Enemies.json")));
            var units = SampleUnits();
            var sim = new BattleSim(sd, enemies, units, new[] { units["DSP_SPEAR"], units["DSP_SNIPER"] }, new HeroDef(), new Rules(), 1);
            for (int t = 0; t < 30 * 200 && sim.End == EndState.Running; t++)
            {
                var cmds = new List<Command>();
                if (t == 30 * 5) cmds.Add(Command.Deploy(t, "DSP_SPEAR", 8, 3, 'W'));
                sim.Step(cmds);
            }
            Assert.AreEqual(EndState.Cleared, sim.End);
            Assert.AreEqual(8, sim.Result.Kills);
        }
    }
}
