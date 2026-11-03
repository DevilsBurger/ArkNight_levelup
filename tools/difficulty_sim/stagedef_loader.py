"""StageDef JSON → 등가 모델 입력(레인 · 포스트 · 커버리지). 07 문서 §4.1"""
from __future__ import annotations
import json, math
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAGES_DIR = HERE / ".." / ".." / "unity" / "Data" / "Stages"
WALK = set("GPSDLTAR")
GROUND_DEPLOY = set("GLTAR")     # 군단원 지상 소집 가능
HERO_OK = set("GTAR")            # 주인공 가능 (L 제외)
DIRS = {"E": (1, 0), "N": (0, 1), "W": (-1, 0), "S": (0, -1)}


def rotate(dx: int, dy: int, facing: str) -> tuple[int, int]:
    # 템플릿은 오른쪽(E)이 전방. (dx 전방, dy 좌측)
    if facing == "E": return (dx, dy)
    if facing == "W": return (-dx, -dy)
    if facing == "N": return (-dy, dx)
    if facing == "S": return (dy, -dx)
    raise ValueError(facing)


@dataclass
class Lane:
    id: str
    tiles: list              # [(x,y)] 출현 → 방어, 인접 타일 연속
    index_of: dict           # (x,y) → index
    @property
    def length(self) -> int:
        return len(self.tiles) - 1


@dataclass
class StageDef:
    id: str
    name: str
    w: int
    h: int
    rows: list
    lives: int
    initial_dp: int
    dp_regen: float
    deploy_limit: int
    hero_mode: str
    hero_default: tuple | None
    sealed: set
    lanes: dict              # id → Lane
    waves: list
    enemy_total: int
    scale: dict
    npc_units: list
    dispatch_units: list
    boss: dict | None
    script: list
    unlock: dict | None
    seed: int
    ground_tiles: list = field(default_factory=list)
    high_tiles: list = field(default_factory=list)

    def tile(self, x: int, y: int) -> str:
        if not (0 <= x < self.w and 0 <= y < self.h): return "X"
        return self.rows[self.h - 1 - y][x]

    def lanes_at(self, xy) -> dict:
        """타일이 속한 레인 → 인덱스"""
        return {lid: ln.index_of[xy] for lid, ln in self.lanes.items() if xy in ln.index_of}

    def last_spawn_time(self) -> float:
        return max(w["t"] + max(w["count"] - 1, 0) * w.get("interval", 0) for w in self.waves)


def expand_route(points: list) -> list:
    tiles = []
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x0 == x1:
            step = 1 if y1 > y0 else -1
            seg = [(x0, y) for y in range(y0, y1 + step, step)]
        else:
            step = 1 if x1 > x0 else -1
            seg = [(x, y0) for x in range(x0, x1 + step, step)]
        if tiles and tiles[-1] == seg[0]: seg = seg[1:]
        tiles.extend(seg)
    return tiles


def load_stage(path: Path) -> StageDef:
    d = json.load(open(path, encoding="utf-8"))
    g = d["grid"]
    lanes = {}
    for lid, pts in d["routes"].items():
        tiles = expand_route([tuple(p) for p in pts])
        lanes[lid] = Lane(lid, tiles, {t: i for i, t in enumerate(tiles)})
    sd = StageDef(
        id=d["id"], name=d["name"], w=g["w"], h=g["h"], rows=g["rows"], lives=d["lives"],
        initial_dp=d["initial_dp"], dp_regen=d.get("dp_regen", 0.7), deploy_limit=d["deploy_limit"],
        hero_mode=d["hero"]["mode"], hero_default=tuple(d["hero"]["default_tile"]) if d["hero"]["default_tile"] else None,
        sealed={tuple(t) for t in d.get("sealed_tiles", [])}, lanes=lanes, waves=d["waves"], enemy_total=d["enemy_total"],
        scale=d.get("scale", {}), npc_units=d.get("npc_units", []), dispatch_units=d.get("dispatch_units", []),
        boss=d.get("boss"), script=d.get("script", []), unlock=d.get("unlock_scenario"), seed=d.get("seed", 0))
    for y in range(sd.h):
        for x in range(sd.w):
            c = sd.tile(x, y)
            if c in GROUND_DEPLOY: sd.ground_tiles.append((x, y))
            elif c == "H": sd.high_tiles.append((x, y))
    return sd


def load_stages(stage_dir: Path = STAGES_DIR, ids: set | None = None) -> list[StageDef]:
    out = []
    for p in sorted(stage_dir.glob("Stage_*.json")):
        sd = load_stage(p)
        if ids is None or sd.id in ids: out.append(sd)
    out.sort(key=lambda s: tuple(int(v) for v in s.id.split("-")))
    return out


def coverage(sd: StageDef, xy: tuple, facing: str, template: list) -> dict:
    """고지대 포스트 커버리지: lane → set(index). 템플릿 안의 레인 타일만 센다."""
    cov = {}
    x0, y0 = xy
    for dx, dy in template:
        rx, ry = rotate(dx, dy, facing)
        t = (x0 + rx, y0 + ry)
        for lid, idx in sd.lanes_at(t).items():
            cov.setdefault(lid, set()).add(idx)
    return cov


def coverage_tiles(sd: StageDef, xy: tuple, facing: str, template: list) -> set:
    x0, y0 = xy
    out = set()
    for dx, dy in template:
        rx, ry = rotate(dx, dy, facing)
        t = (x0 + rx, y0 + ry)
        if sd.tile(*t) != "X" or True: out.add(t)
    return out


def best_facing(sd: StageDef, xy: tuple, template: list, weights: dict | None = None) -> tuple[str, dict]:
    best, bcov, bscore = "E", {}, -1.0
    for f in DIRS:
        cov = coverage(sd, xy, f, template)
        score = 0.0
        for lid, idxs in cov.items():
            wgt = (weights or {}).get(lid, 1.0)
            score += wgt * len(idxs)
        if score > bscore:
            best, bcov, bscore = f, cov, score
    return best, bcov


if __name__ == "__main__":
    for sd in load_stages():
        print(sd.id, sd.name, {k: v.length for k, v in sd.lanes.items()}, "ground", len(sd.ground_tiles), "high", len(sd.high_tiles),
              "last_spawn", sd.last_spawn_time())
