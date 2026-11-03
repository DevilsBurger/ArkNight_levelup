// 최소 JSON 파서(의존성 없음). StageDef · Enemies 로딩 전용 — 숫자 · 문자열 · 배열 · 객체 · bool · null.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace Army.Core
{
    public static class Json
    {
        public static object Parse(string s) { int i = 0; var v = ParseValue(s, ref i); return v; }

        private static void Ws(string s, ref int i) { while (i < s.Length && char.IsWhiteSpace(s[i])) i++; }

        private static object ParseValue(string s, ref int i)
        {
            Ws(s, ref i);
            if (i >= s.Length) throw new FormatException("eof");
            char c = s[i];
            if (c == '{') return ParseObject(s, ref i);
            if (c == '[') return ParseArray(s, ref i);
            if (c == '"') return ParseString(s, ref i);
            if (s.Length - i >= 4 && string.CompareOrdinal(s, i, "true", 0, 4) == 0) { i += 4; return true; }
            if (s.Length - i >= 5 && string.CompareOrdinal(s, i, "false", 0, 5) == 0) { i += 5; return false; }
            if (s.Length - i >= 4 && string.CompareOrdinal(s, i, "null", 0, 4) == 0) { i += 4; return null; }
            int start = i;
            while (i < s.Length && (char.IsDigit(s[i]) || s[i] == '-' || s[i] == '+' || s[i] == '.' || s[i] == 'e' || s[i] == 'E')) i++;
            return double.Parse(s.Substring(start, i - start), CultureInfo.InvariantCulture);
        }

        private static Dictionary<string, object> ParseObject(string s, ref int i)
        {
            var d = new Dictionary<string, object>(); i++; Ws(s, ref i);
            if (s[i] == '}') { i++; return d; }
            while (true)
            {
                Ws(s, ref i); string k = ParseString(s, ref i); Ws(s, ref i);
                if (s[i] != ':') throw new FormatException("colon"); i++;
                d[k] = ParseValue(s, ref i); Ws(s, ref i);
                if (s[i] == ',') { i++; continue; }
                if (s[i] == '}') { i++; return d; }
                throw new FormatException("object");
            }
        }

        private static List<object> ParseArray(string s, ref int i)
        {
            var a = new List<object>(); i++; Ws(s, ref i);
            if (s[i] == ']') { i++; return a; }
            while (true)
            {
                a.Add(ParseValue(s, ref i)); Ws(s, ref i);
                if (s[i] == ',') { i++; continue; }
                if (s[i] == ']') { i++; return a; }
                throw new FormatException("array");
            }
        }

        private static string ParseString(string s, ref int i)
        {
            if (s[i] != '"') throw new FormatException("string"); i++;
            var sb = new StringBuilder();
            while (s[i] != '"')
            {
                if (s[i] == '\\')
                {
                    i++; char e = s[i];
                    switch (e)
                    {
                        case 'n': sb.Append('\n'); break; case 't': sb.Append('\t'); break; case 'r': sb.Append('\r'); break;
                        case 'u': sb.Append((char)Convert.ToInt32(s.Substring(i + 1, 4), 16)); i += 4; break;
                        default: sb.Append(e); break;
                    }
                    i++;
                }
                else { sb.Append(s[i]); i++; }
            }
            i++; return sb.ToString();
        }

        // ---- 편의 접근자 ----
        public static Dictionary<string, object> Obj(object o) => (Dictionary<string, object>)o;
        public static List<object> Arr(object o) => (List<object>)o;
        public static int Int(object o) => (int)Math.Round((double)o);
        public static int Milli(object o) => (int)Math.Round((double)o * 1000.0);
        public static string Str(object o) => o as string;
        public static T Get<T>(Dictionary<string, object> d, string k, T dflt) { object v; return d.TryGetValue(k, out v) && v != null ? (T)v : dflt; }
    }

    public static class StageLoader
    {
        public static StageDef FromJson(string json)
        {
            var d = Json.Obj(Json.Parse(json)); var sd = new StageDef();
            sd.Id = Json.Str(d["id"]); sd.Chapter = Json.Int(d["chapter"]); sd.Name = Json.Str(d["name"]);
            var g = Json.Obj(d["grid"]); sd.W = Json.Int(g["w"]); sd.H = Json.Int(g["h"]); sd.Grid = new Tile[sd.W * sd.H];
            var rows = Json.Arr(g["rows"]);
            for (int r = 0; r < sd.H; r++) { string row = Json.Str(rows[r]); int y = sd.H - 1 - r; for (int x = 0; x < sd.W; x++) sd.Grid[y * sd.W + x] = TileCodes.Parse(row[x]); }
            sd.Lives = Json.Int(d["lives"]); sd.InitialDp10 = Json.Int(d["initial_dp"]) * 10; sd.DpRegenMilliPerSec = Json.Milli(d["dp_regen"]);
            sd.DeployLimit = Json.Int(d["deploy_limit"]);
            var hero = Json.Obj(d["hero"]); sd.HeroMode = Json.Str(hero["mode"]);
            object ht; if (hero.TryGetValue("default_tile", out ht) && ht != null) { var p = Json.Arr(ht); sd.HeroDefault = new Point(Json.Int(p[0]), Json.Int(p[1])); }
            foreach (var t in Json.Arr(Json.Get<object>(d, "sealed_tiles", new List<object>()))) { var p = Json.Arr(t); sd.Sealed.Add(new Point(Json.Int(p[0]), Json.Int(p[1]))); }
            foreach (var kv in Json.Obj(d["routes"])) sd.Routes.Add(MakeRoute(kv.Key, kv.Value, false));
            object air; if (d.TryGetValue("routes_air", out air) && air != null) foreach (var kv in Json.Obj(air)) sd.Routes.Add(MakeRoute(kv.Key, kv.Value, true));
            foreach (var w in Json.Arr(d["waves"]))
            {
                var o = Json.Obj(w);
                sd.Waves.Add(new WaveDef { TimeMilli = Json.Milli(o["t"]), EnemyId = Json.Str(o["enemy"]), Route = Json.Str(o["route"]), Count = Json.Int(o["count"]), IntervalMilli = Json.Milli(Json.Get<object>(o, "interval", 0.0)) });
            }
            object sc; if (d.TryGetValue("scale", out sc) && sc != null) { var o = Json.Obj(sc); sd.ScaleHpPct = (int)Math.Round((double)o["hp"] * 100); sd.ScaleAtkPct = (int)Math.Round((double)o["atk"] * 100); sd.ScaleDefPct = (int)Math.Round((double)o["def"] * 100); }
            foreach (var n in Json.Arr(Json.Get<object>(d, "npc_units", new List<object>())))
            {
                var o = Json.Obj(n); var p = Json.Arr(o["tile"]);
                sd.Npcs.Add(new NpcDef { Id = Json.Str(o["id"]), Unit = Json.Str(o["unit"]), Tile = new Point(Json.Int(p[0]), Json.Int(p[1])), Dir = Json.Get<string>(o, "dir", "E")[0], Level = Json.Int(Json.Get<object>(o, "level", 10.0)), Role = Json.Get<string>(o, "role", "companion") });
            }
            sd.Seed = (uint)Json.Int(Json.Get<object>(d, "seed", 0.0));
            return sd;
        }

        private static RouteDef MakeRoute(string id, object pts, bool air)
        {
            var list = new List<Point>();
            foreach (var p in Json.Arr(pts)) { var q = Json.Arr(p); list.Add(new Point(Json.Int(q[0]), Json.Int(q[1]))); }
            return new RouteDef { Id = id, Air = air, Tiles = RouteDef.Expand(list) };
        }
    }

    public static class EnemyLoader
    {
        /// <summary>unity/Data/Enemies.json → id → EnemyDef (변형 · 보스 포함). 변형 배율은 Enemies.json 의 note 규칙(elite ×2.0/×1.4/×1.3).</summary>
        public static Dictionary<string, EnemyDef> FromJson(string json)
        {
            var d = Json.Obj(Json.Parse(json)); var table = new Dictionary<string, EnemyDef>();
            foreach (var b in Json.Arr(d["bases"])) { var e = Base(Json.Obj(b)); table[e.Id] = e; }
            foreach (var v in Json.Arr(d["variants"]))
            {
                var o = Json.Obj(v); var src = table[Json.Str(o["base"])]; var e = Clone(src); e.Id = Json.Str(o["id"]);
                string variant = Json.Str(o["variant"]);
                if (variant == "elite") { e.Kind = "elite"; e.Hp = e.Hp * 2; e.Atk = Fixed32.Percent(e.Atk, 140); e.Def = Fixed32.Percent(e.Def, 130); }
                object ov; if (o.TryGetValue("override", out ov) && ov != null) Apply(e, Json.Obj(ov));
                e.DpReward = Json.Int(Json.Get<object>(o, "dp", 1.0)); e.SpReward = Json.Int(Json.Get<object>(o, "sp", 1.0));
                table[e.Id] = e;
            }
            foreach (var b in Json.Arr(d["bosses"]))
            {
                var o = Json.Obj(b); var e = Base(o); e.Kind = "boss"; e.DpReward = 5; e.SpReward = 5;
                object ab; if (o.TryGetValue("abilities", out ab)) foreach (var a in Json.Arr(ab)) ApplyAbility(e, Json.Str(a));
                table[e.Id] = e;
            }
            return table;
        }

        private static EnemyDef Base(Dictionary<string, object> o)
        {
            var e = new EnemyDef { Id = Json.Str(o["id"]) }; Apply(e, o); return e;
        }

        private static void Apply(EnemyDef e, Dictionary<string, object> o)
        {
            object v;
            if (o.TryGetValue("hp", out v)) e.Hp = Json.Int(v); if (o.TryGetValue("atk", out v)) e.Atk = Json.Int(v);
            if (o.TryGetValue("def", out v)) e.Def = Json.Int(v); if (o.TryGetValue("res", out v)) e.Res = Json.Int(v);
            if (o.TryGetValue("speed", out v)) e.SpeedMilli = Json.Milli(v); if (o.TryGetValue("weight", out v)) e.Weight = Json.Int(v);
            if (o.TryGetValue("flying", out v) && v != null) e.Flying = (bool)v; if (o.TryGetValue("interval", out v)) e.IntervalMilli = Json.Milli(v);
            if (o.TryGetValue("ability", out v) && v != null) ApplyAbility(e, Json.Str(v));
        }

        private static void ApplyAbility(EnemyDef e, string ab)
        {
            foreach (var raw in ab.Split(','))
            {
                string tok = raw.Trim();
                if (tok.StartsWith("ranged:")) e.RangedTiles = int.Parse(tok.Substring(7));
                else if (tok.StartsWith("arts_ranged:")) { e.RangedTiles = int.Parse(tok.Substring(12)); e.Arts = true; }
                else if (tok.StartsWith("charge")) e.Charge = true;
                else if (tok.StartsWith("stealth")) e.Stealth = true;
                else if (tok.StartsWith("revive")) e.Revive = true;
                else if (tok == "flying") e.Flying = true;
                else if (tok.StartsWith("enrage_unblocked:")) e.EnrageMilli = (int)Math.Round(double.Parse(tok.Substring(17), CultureInfo.InvariantCulture) * 1000);
            }
        }

        private static EnemyDef Clone(EnemyDef s) => new EnemyDef
        {
            Id = s.Id, Kind = s.Kind, Hp = s.Hp, Atk = s.Atk, Def = s.Def, Res = s.Res, SpeedMilli = s.SpeedMilli, Weight = s.Weight, Flying = s.Flying,
            RangedTiles = s.RangedTiles, Arts = s.Arts, Charge = s.Charge, Stealth = s.Stealth, Revive = s.Revive, EnrageMilli = s.EnrageMilli, IntervalMilli = s.IntervalMilli, DpReward = s.DpReward, SpReward = s.SpReward
        };
    }
}
