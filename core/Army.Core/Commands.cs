// 입력 명령과 로그. 10 TDD §4.5 · 02 GDD §9.2. 모든 플레이어 조작은 Command 로만 코어에 들어간다.
using System.Collections.Generic;

namespace Army.Core
{
    public enum CommandType : byte { HeroPlace, Deploy, Retreat, Skill, HeroMove, Ult }

    public struct Command
    {
        public int Tick; public CommandType Type; public string Unit; public int X, Y; public char Dir;
        public static Command HeroPlace(int tick, int x, int y) => new Command { Tick = tick, Type = CommandType.HeroPlace, X = x, Y = y };
        public static Command Deploy(int tick, string unit, int x, int y, char dir) => new Command { Tick = tick, Type = CommandType.Deploy, Unit = unit, X = x, Y = y, Dir = dir };
        public static Command Retreat(int tick, string unit) => new Command { Tick = tick, Type = CommandType.Retreat, Unit = unit };
        public static Command Skill(int tick, string unit) => new Command { Tick = tick, Type = CommandType.Skill, Unit = unit };
        public static Command HeroMove(int tick, int x, int y) => new Command { Tick = tick, Type = CommandType.HeroMove, X = x, Y = y };
        public static Command Ult(int tick, char dir) => new Command { Tick = tick, Type = CommandType.Ult, Dir = dir };
    }

    /// <summary>틱 순으로 정렬된 명령 열. 자동 지휘 · 리플레이 · 서버 검증의 입력.</summary>
    public sealed class InputLog
    {
        public string StageId; public uint Seed; public string CoreVersion = "0.1.0";
        public readonly List<Command> Commands = new List<Command>();
        public void Add(Command c) { Commands.Add(c); }
        public int Count => Commands.Count;
    }
}
