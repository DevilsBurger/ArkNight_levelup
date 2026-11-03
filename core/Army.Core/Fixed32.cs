// 결정론 고정소수점: 1/1000 단위 정수. 10 TDD §4.1. Unity · 서버 · 에디터에서 동일 결과.
namespace Army.Core
{
    public readonly struct Fixed32
    {
        public const int Scale = 1000;
        public readonly int Raw;
        public Fixed32(int raw) { Raw = raw; }
        public static Fixed32 FromInt(int v) => new Fixed32(v * Scale);
        public static Fixed32 FromMilli(int milli) => new Fixed32(milli);
        public static readonly Fixed32 Zero = new Fixed32(0);
        public static readonly Fixed32 One = new Fixed32(Scale);
        public int Floor => Raw >= 0 ? Raw / Scale : -((-Raw + Scale - 1) / Scale);
        public static Fixed32 operator +(Fixed32 a, Fixed32 b) => new Fixed32(a.Raw + b.Raw);
        public static Fixed32 operator -(Fixed32 a, Fixed32 b) => new Fixed32(a.Raw - b.Raw);
        public static Fixed32 operator *(Fixed32 a, Fixed32 b) => new Fixed32((int)(((long)a.Raw * b.Raw) / Scale));
        public static Fixed32 operator /(Fixed32 a, Fixed32 b) => new Fixed32((int)(((long)a.Raw * Scale) / b.Raw));
        public static Fixed32 operator *(Fixed32 a, int b) => new Fixed32(a.Raw * b);
        public static bool operator <(Fixed32 a, Fixed32 b) => a.Raw < b.Raw;
        public static bool operator >(Fixed32 a, Fixed32 b) => a.Raw > b.Raw;
        public static bool operator <=(Fixed32 a, Fixed32 b) => a.Raw <= b.Raw;
        public static bool operator >=(Fixed32 a, Fixed32 b) => a.Raw >= b.Raw;
        public static Fixed32 Max(Fixed32 a, Fixed32 b) => a.Raw >= b.Raw ? a : b;
        public static Fixed32 Min(Fixed32 a, Fixed32 b) => a.Raw <= b.Raw ? a : b;
        /// <summary>a × pct / 100, 내림. 백분율 계산 순서를 고정한다.</summary>
        public static int Percent(int a, int pct) => (int)(((long)a * pct) / 100);
        public override string ToString() => (Raw / (double)Scale).ToString("0.000");
    }

    /// <summary>결정론 난수. 시드가 같으면 모든 플랫폼에서 같은 열.</summary>
    public sealed class XorShift32
    {
        private uint _s;
        public XorShift32(uint seed) { _s = seed == 0 ? 2463534242u : seed; }
        public uint Next() { uint x = _s; x ^= x << 13; x ^= x >> 17; x ^= x << 5; _s = x; return x; }
        /// <summary>[0, n)</summary>
        public int NextInt(int n) => (int)(Next() % (uint)n);
        /// <summary>pct(0~100) 확률로 true</summary>
        public bool Chance(int pct) => NextInt(100) < pct;
    }
}
