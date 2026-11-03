"""타워 디펜스 등가 모델 (07 문서 §4): 레인(경로) 위 1차원 흐름 + 포스트(저지 · 사격 지점) 전투 + 행동 정책.
2D 공간 · 방향 · 애니메이션 · 30 Hz 틱은 쓰지 않는다. 전투는 dt(0.5s) 단위 DPS 흐름으로 치환하고,
난수는 플레이어 정책(판단 간격 · 실수 · 포스트 선택)에서만 나온다."""
from __future__ import annotations
import json, math, random
from pathlib import Path
import yaml

from stagedef_loader import (StageDef, load_stages, best_facing, coverage, coverage_tiles,
                             HERO_OK, GROUND_DEPLOY)

HERE = Path(__file__).resolve().parent
KIND_W = {"normal": 1.0, "elite": 2.0, "boss": 5.0}
GROUND_ORDER = ["shield", "spear", "special"]
RANGED_ORDER = ["sniper", "caster"]


def load_params(path: Path | None = None) -> dict:
    with open(path or HERE / "params.yaml", encoding="utf-8") as f:
        P = yaml.safe_load(f)
    P["units"].update(P.get("units_more", {}))
    P["squads"].update({k: dict(hero="awakened", **v) for k, v in P.get("squads_more", {}).items()})
    return P


def load_policies(path: Path | None = None) -> dict:
    with open(path or HERE / "policies.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)["policies"]


def load_enemy_table(P: dict) -> dict:
    src = (HERE / P["enemies"]["source"]).resolve()
    e = json.load(open(src, encoding="utf-8"))
    table = {}
    for b in e["bases"]:
        table[b["id"]] = dict(b, kind="normal", dp=1, sp=1)
    vm = P["enemies"]["variant_mult"]
    for v in e["variants"]:
        base = dict(table[v["base"]])
        if v["variant"] in vm:
            for k, m in vm[v["variant"]].items():
                base[k] = base[k] * m
        base.update(v.get("override", {}))
        base.update(id=v["id"], name=v["name"], kind="elite" if v["variant"] == "elite" else "normal", dp=v.get("dp", 1), sp=v.get("sp", 1))
        table[v["id"]] = base
    for b in e["bosses"]:
        table[b["id"]] = dict(b, kind="boss", dp=b.get("dp", 5), sp=b.get("sp_per_phase", 5), ability=",".join(b.get("abilities", [])))
    return table


def eff_damage(atk: float, dmg: str, tdef: float, tres: float, min_ratio: float) -> float:
    if atk <= 0: return 0.0
    if dmg == "arts":
        return max(atk * (1.0 - tres / 100.0), atk * min_ratio)
    if dmg == "true":
        return atk
    return max(atk - tdef, atk * min_ratio)


# ---------------------------------------------------------------- 성장 → 능력치
def build_hero_stats(P: dict, mode: str, growth: dict, ov: dict) -> dict:
    H = P["hero"]
    if mode == "pre":
        s = dict(H["pre"]); s.update(relocate=False, kill_heal=0.0, momentum_max=0, cmd_dp=1.0, cmd_legion=0.0,
                                     relocate_cd=H["relocate_cd"], knockdown=H["knockdown"], revive_hp=H["revive_hp"])
        s["hp"] *= ov.get("hero_hp_mult", 1.0); s["atk"] *= ov.get("hero_atk_mult", 1.0)
        return s
    b = H["base"]; L = growth["hero_level"]; mult = 1.0 + H["level_growth"] * (L - 1)
    st = growth.get("stats", {}); E = H["stat_effects"]
    atk = b["atk"] * (mult + E["str_atk"] * st.get("str", 0))
    hp = b["hp"] * (mult + E["vit_hp"] * st.get("vit", 0))
    df = b["def"] * (mult + E["def_def"] * st.get("def", 0))
    res = min(50.0, b["res"] + E["def_res"] * st.get("def", 0))
    interval = b["interval"] * (1.0 - min(E["agi_interval_cap"], E["agi_interval"] * st.get("agi", 0)))
    cd = H["relocate_cd"] - min(E["agi_cd_cap"], E["agi_cd"] * st.get("agi", 0))
    cmd = st.get("cmd", 0)
    s = dict(hp=hp, atk=atk, **{"def": df}, res=res, block=b["block"], interval=interval, range_front=b["range_front"],
             max_targets=b["max_targets"], relocate=True, relocate_cd=cd, knockdown=H["knockdown"], revive_hp=H["revive_hp"],
             kill_heal=0.0, momentum_max=H["momentum"]["max"], cmd_dp=1.0 + E["cmd_dp"] * cmd,
             cmd_legion=min(E["cmd_legion_cap"], E["cmd_legion"] * cmd))
    for node in growth.get("tree", []):
        t = H["tree"].get(node, {})
        if "range_front" in t: s["range_front"] = t["range_front"]
        if "kill_heal" in t: s["kill_heal"] = t["kill_heal"]
        if "momentum_max" in t: s["momentum_max"] = t["momentum_max"]
        if "hp_mult" in t: s["hp"] *= t["hp_mult"]
        if "knockdown" in t: s["knockdown"] = t["knockdown"]
        if "block_add" in t: s["block"] += t["block_add"]
    s["hp"] *= ov.get("hero_hp_mult", 1.0); s["atk"] *= ov.get("hero_atk_mult", 1.0)
    s["relocate_cd"] = ov.get("relocate_cd", s["relocate_cd"])
    return s


def build_unit_stats(P: dict, uid: str, growth: dict, cmd_legion: float, ov: dict) -> dict:
    u = P["units"][uid]; c = dict(P["classes"][u["class"]]); LG = P["legion"]
    rar = u.get("rarity", 4)
    level = u.get("fixed_level", growth["legion_level"]); awaken = 0 if "fixed_level" in u else growth["awaken"]
    mult = (1.0 + LG["level_growth"] * (level - 1)) * LG["awaken_mult"][awaken] * LG["rarity_mult"][rar] * (1.0 + cmd_legion) * ov.get("legion_mult", 1.0)
    s = dict(uid=uid, cls=u["class"], pos=c["pos"], hp=c["hp"] * mult, atk=c["atk"] * mult, res=c["res"], block=u.get("block", c["block"]),
             cost=max(1, c["cost"] + LG["rarity_cost_add"][rar]), redeploy=c["redeploy"], interval=c["interval"], range=c["range"],
             dmg=c["dmg"], prio=c.get("prio"), slow=c.get("slow", 0.0), skill=dict(c.get("skill", {})), rarity=rar, level=level)
    s["def"] = c["def"] * mult
    rank = 1 if "fixed_level" in u else growth["skill_rank"]
    s["skill_rank_mult"] = 1.0 + LG["skill_rank_mult"] * (rank - 1)
    if awaken >= 1 and s["range"] == "R3": s["range"] = "R3p"
    return s


def build_enemy_stats(table: dict, eid: str, scale: dict, ov: dict) -> dict:
    e = table[eid]
    ab = e.get("ability") or ""
    ranged = 0
    for tok in ab.split(","):
        tok = tok.strip()
        if tok.startswith("ranged:") or tok.startswith("arts_ranged:"):
            ranged = int(tok.split(":")[1])
    boss = e["kind"] == "boss"
    hp_m = ov.get("boss_hp_mult", 1.0) if boss else ov.get("enemy_hp_mult", 1.0)
    atk_m = ov.get("boss_atk_mult", 1.0) if boss else ov.get("enemy_atk_mult", 1.0)
    sp_m = ov.get("boss_speed_mult", 1.0) if boss else ov.get("enemy_speed_mult", 1.0)
    if boss: scale = {}   # 보스 수치는 챕터 배율 미적용 최종값
    m = ov.get("chapter_scale_mult", 1.0)
    scale = {k: 1.0 + (v - 1.0) * m for k, v in scale.items()}   # 배율의 초과분만 조절
    enrage = 1.0
    for tok in ab.split(","):
        if tok.strip().startswith("enrage_unblocked:"): enrage = float(tok.split(":")[1])
    return dict(id=eid, kind=e["kind"], enrage=enrage, def_mult=1.0, interval=e.get("interval", 1.0), hp=e["hp"] * scale.get("hp", 1.0) * hp_m,
                atk=e["atk"] * scale.get("atk", 1.0) * atk_m, **{"def": e["def"] * scale.get("def", 1.0)},
                res=e["res"], speed=e["speed"] * sp_m, flying=bool(e.get("flying")), ranged=ranged,
                arts="arts" in ab, charge="charge" in ab, stealth="stealth" in ab, revive="revive" in ab,
                dp=e.get("dp", 1), sp=e.get("sp", 1), is_boss=e["kind"] == "boss")


# ---------------------------------------------------------------- 엔티티
class Enemy:
    __slots__ = ("st", "lane", "p", "hp", "blocked_by", "stun", "slow", "charge_pending", "revived", "invuln", "alive", "uid")
    def __init__(self, st: dict, lane: str, uid: int):
        self.st = st; self.lane = lane; self.p = 0.0; self.hp = st["hp"]; self.blocked_by = None
        self.stun = 0.0; self.slow = 0.0; self.charge_pending = st["charge"]; self.revived = False; self.invuln = 0.0
        self.alive = True; self.uid = uid


class Unit:
    """지상 · 고지대 아군. 주인공 · NPC · 민간인도 이 클래스."""
    def __init__(self, st: dict, tile: tuple, kind: str, card=None):
        self.st = st; self.tile = tile; self.kind = kind   # hero | legion | npc | civilian
        self.card = card
        self.hp = st["hp"]; self.max_hp = st["hp"]; self.block = st["block"]
        self.blocked: list[Enemy] = []
        self.lanes: dict = {}      # 지상: lane → idx
        self.cov: dict = {}        # 고지대: lane → set(idx)
        self.cov_tiles: set = set()
        self.facing = "E"
        self.sp = 0.0; self.skill_t = 0.0; self.alive = True; self.kd = 0.0; self.deployed_t = 0.0
        self.attack_acc = 0.0
        # hero only
        self.moving = 0.0; self.cd = 0.0; self.momentum = 0; self.last_kill_t = -99.0; self.ult_sp = 0.0; self.kills = 0
        self.down_count = 0; self.slow_cov = 0.0

    @property
    def active(self) -> bool:
        return self.alive and self.kd <= 0 and self.moving <= 0

    @property
    def is_ground(self) -> bool:
        return self.st.get("pos", "G") == "G"

    def free_slots(self) -> int:
        add = self.st["skill"].get("block_add", 0) if (self.skill_t > 0 and self.kind != "hero") else 0
        return self.block + add - len(self.blocked)

    def def_eff(self) -> float:
        d = self.st["def"]
        if self.skill_t > 0 and self.kind != "hero": d *= self.st["skill"].get("def_mult", 1.0)
        return d


class Card:
    def __init__(self, st: dict):
        self.st = st; self.uid = st["uid"]; self.deploy_count = 0; self.cooldown = 0.0; self.unit: Unit | None = None

    def current_cost(self, mults: list) -> int:
        return min(99, int(self.st["cost"] * mults[min(self.deploy_count, len(mults) - 1)]))

    @property
    def available(self) -> bool:
        return self.unit is None and self.cooldown <= 0


# ---------------------------------------------------------------- 시뮬레이션
class Sim:
    def __init__(self, sd: StageDef, P: dict, pol: dict, growth: dict, table: dict, seed: int, ov: dict | None = None,
                 squad: dict | None = None):
        self.sd = sd; self.P = P; self.pol = pol; self.growth = growth; self.table = table; self.ov = ov or {}
        self.rng = random.Random(seed)
        self.dt = P["sim"]["dt"]; self.R = P["rules"]
        self.squad = squad or P["squads"].get(sd.id, {"hero": "awakened", "legion": [], "optional": []})
        self.cov_cache = {}

    # ---------- 준비
    def setup(self):
        sd, P = self.sd, self.P
        self.t = 0.0; self.lives = sd.lives; self.dp = float(sd.initial_dp) + self.ov.get("initial_dp_add", 0.0)
        self.dp_regen = sd.dp_regen * self.ov.get("dp_regen_mult", 1.0)
        self.deploy_limit = sd.deploy_limit + self.ov.get("deploy_limit_add", 0)
        self.sealed = set(sd.sealed)
        self.enemies: list[Enemy] = []; self.units: list[Unit] = []; self.occ: dict = {}
        self.spawn_q = []
        for w in sd.waves:
            for k in range(w["count"]):
                self.spawn_q.append((w["t"] + k * w.get("interval", 0.0), w["enemy"], w["route"]))
        self.spawn_q.sort(key=lambda z: z[0]); self.spawn_i = 0; self.last_spawn = sd.last_spawn_time()
        self.uid_seq = 0
        # 주인공
        hero_mode = self.squad.get("hero", "awakened")
        if hero_mode == "pre" and sd.hero_mode != "pre_awakening": hero_mode = "awakened"
        self.hero_stats = build_hero_stats(P, hero_mode, self.growth, self.ov)
        self.hero = Unit(self.hero_stats, sd.hero_default, "hero")
        self.hero.st["pos"] = "G"; self.hero.st["skill"] = {}
        self.hero.lanes = sd.lanes_at(sd.hero_default) if sd.hero_default else {}
        self.hero_present = sd.hero_default is not None
        if self.hero_present:
            self.units.append(self.hero); self.occ[sd.hero_default] = self.hero
        # NPC
        self.npcs: dict[str, Unit] = {}
        for n in sd.npc_units:
            st = build_unit_stats(P, n["unit"], dict(self.growth, legion_level=n.get("level", 10), awaken=0, skill_rank=1), 0.0, self.ov)
            u = Unit(st, tuple(n["tile"]), "civilian" if n["unit"] == "CIVILIAN" else "npc")
            self.place(u, tuple(n["tile"]), n.get("dir", "E"))
            self.npcs[n["id"]] = u
        # 카드
        legion = list(self.squad.get("legion", []))
        if self.growth.get("include_optional"):
            merged = legion + [u for u in self.squad.get("optional", []) if u not in legion]
            order = {uid: i for i, uid in enumerate(merged)}
            merged.sort(key=lambda uid: (-P["units"][uid].get("rarity", 4), order[uid]))
            legion = merged[:8]
        if self.pol.get("deploy") == "none": legion = []
        self.cards = [Card(build_unit_stats(P, uid, self.growth, self.hero_stats.get("cmd_legion", 0.0), self.ov)) for uid in legion]
        self.scripts = [s for s in sd.script if s.get("event") == "npc_down"]
        tut = [s for s in sd.script if s.get("event") == "tutorial" and s.get("key") == "hero_relocate"]
        self.tutorial_relocate = (tut[0]["t"], 1e9) if tut else None   # 1-3은 스테이지 전체가 안내 구간(웨이브마다 화살표)
        self.boss_phase = -1
        # 지표
        self.leaks = 0; self.knockdowns = 0; self.legion_deaths = 0; self.relocates = 0; self.ult_uses = 0
        self.hero_kills = 0; self.kills = 0; self.dp_spent = 0.0; self.dp_earned_kill = 0.0; self.fail = None
        self.next_decision = 0.0; self.deploys = 0; self.retreats = 0; self.skill_uses = 0; self.leak_log = []
        self.traps_used = set()
        self.spawned = 0

    # ---------- 배치
    def place(self, u: Unit, tile: tuple, facing: str = "E"):
        u.tile = tile; u.facing = facing; u.alive = True; u.hp = u.max_hp; u.blocked = []; u.deployed_t = self.t
        u.sp = self.P["sim"]["initial_sp_ratio"] * u.st["skill"].get("sp", 0) if u.st["skill"].get("mode") == "manual" else 0.0
        u.skill_t = u.st["skill"].get("dur", 0) if u.st["skill"].get("mode") == "passive" else 0.0
        self.occ[tile] = u
        if u not in self.units: self.units.append(u)
        if u.is_ground:
            u.lanes = self.sd.lanes_at(tile)
            # 타일 위에 서 있던 적을 저지
            for e in self.enemies:
                if e.alive and e.blocked_by is None and not e.st["flying"] and e.lane in u.lanes:
                    idx = u.lanes[e.lane]
                    if idx <= e.p < idx + 1 and u.free_slots() > 0 and u.block > 0:
                        e.blocked_by = u; u.blocked.append(e); e.p = float(idx)
        else:
            tmpl = self.P["ranges"][u.st["range"]]
            u.cov = coverage(self.sd, tile, facing, tmpl)
            u.cov_tiles = coverage_tiles(self.sd, tile, facing, tmpl)

    def remove_unit(self, u: Unit):
        for e in u.blocked:
            e.blocked_by = None
        u.blocked = []; u.alive = False
        self.occ.pop(u.tile, None)
        if u in self.units: self.units.remove(u)

    def deploy_card(self, card: Card, tile: tuple, facing: str) -> bool:
        cost = card.current_cost(self.R["redeploy_mult"])
        if self.dp < cost or tile in self.occ or not card.available: return False
        if self.deployed_legion() >= self.deploy_limit: return False
        u = Unit(card.st, tile, "legion", card); card.unit = u
        self.dp -= cost; self.dp_spent += cost; card.deploy_count += 1; self.deploys += 1
        self.place(u, tile, facing)
        return True

    def retreat(self, u: Unit):
        if u.kind != "legion" or not u.alive: return
        card = u.card; refund = int(card.current_cost(self.R["redeploy_mult"]) * self.R["refund"])
        # current_cost 는 이미 deploy_count 증가 후 → 직전 소집 코스트로 환급
        prev = min(99, int(card.st["cost"] * self.R["redeploy_mult"][min(card.deploy_count - 1, 2)]))
        self.dp = min(self.R["dp_cap"], self.dp + int(prev * self.R["refund"]))
        self.remove_unit(u); card.unit = None; card.cooldown = card.st["redeploy"]; self.retreats += 1

    def deployed_legion(self) -> int:
        return sum(1 for u in self.units if u.kind == "legion" and u.alive)

    # ---------- 질의
    def lane_enemies(self, lid: str) -> list[Enemy]:
        return [e for e in self.enemies if e.alive and e.lane == lid]

    def ground_blockers(self, lid: str) -> list[Unit]:
        return [u for u in self.units if u.alive and u.active and u.is_ground and u.block > 0 and lid in u.lanes and u.kind != "civilian"]

    def open_threat(self, lid: str) -> tuple[float, float]:
        """(열린 위협 가중치, 열린 적 중 최대 p). 앞에 저지 가능한 아군이 없는 지상 적."""
        if self.sd.lanes[lid].air: return 0.0, -1.0
        blk = self.ground_blockers(lid)
        w = 0.0; maxp = -1.0; L = self.sd.lanes[lid].length
        for e in self.lane_enemies(lid):
            if e.blocked_by is not None or e.st["flying"]: continue
            idx_ahead = [u.lanes[lid] for u in blk if u.lanes[lid] > e.p and u.free_slots() > 0]
            if idx_ahead: continue
            w += KIND_W[e.st["kind"]] * (1.0 + e.p / max(1, L)); maxp = max(maxp, e.p)
        return w, maxp

    def incoming_flying(self, lid: str, horizon: float) -> int:
        n = 0
        for i in range(self.spawn_i, len(self.spawn_q)):
            tt, eid, lane = self.spawn_q[i]
            if tt > self.t + horizon: break
            if lane == lid and self.table.get(eid, {}).get("flying"): n += 1
        return n

    def incoming_soon(self, lid: str, horizon: float) -> int:
        n = 0
        for i in range(self.spawn_i, len(self.spawn_q)):
            tt, eid, lane = self.spawn_q[i]
            if tt > self.t + horizon: break
            if lane == lid: n += 1
        return n

    def hero_allowed(self, tile: tuple) -> bool:
        return self.sd.tile(*tile) in HERO_OK and tile not in self.sealed and tile not in self.occ

    def lane_ground_candidates(self, lid: str, hero: bool, min_idx: float = 0.0) -> list[tuple]:
        ln = self.sd.lanes[lid]; out = []
        for i, t in enumerate(ln.tiles[1:-1], start=1):
            if i <= min_idx: continue
            code = self.sd.tile(*t)
            ok = (code in HERO_OK and t not in self.sealed) if hero else (code in GROUND_DEPLOY)
            if ok and t not in self.occ: out.append(t)
        return out

    def ranged_cov_at(self, lid: str, idx: int) -> int:
        return sum(1 for u in self.units if u.alive and not u.is_ground and u.st["dmg"] in ("phys", "arts") and idx in u.cov.get(lid, ()))

    def best_ground_post(self, lid: str, hero: bool) -> tuple | None:
        w, maxp = self.open_threat(lid)
        cands = self.lane_ground_candidates(lid, hero, min_idx=maxp if maxp >= 0 else -1)
        if not cands: return None
        ln = self.sd.lanes[lid]
        hero_idx = self.hero.lanes.get(lid) if (self.hero_present and not hero) else None
        def score(t):
            nl = len(self.sd.lanes_at(t)); idx = ln.index_of[t]
            front = 1.5 if (hero_idx is not None and idx < hero_idx) else 0.0   # 주인공 앞에서 받는 자리 선호
            return 3.0 * nl + 1.0 * self.ranged_cov_at(lid, idx) + 0.02 * idx + front
        cands.sort(key=score, reverse=True)
        return cands[0] if self.rng.random() < self.pol.get("post_quality", 1.0) else self.rng.choice(cands)

    def best_high_post(self, st: dict, target_lane: str | None) -> tuple | None:
        tmpl = self.P["ranges"][st["range"]]
        weights = {lid: 1.0 for lid in self.sd.lanes}
        for u in self.units:
            if u.alive and u.is_ground and u.kind != "civilian":
                for lid in u.lanes: weights[lid] = weights.get(lid, 1.0) + 1.0
        if target_lane: weights[target_lane] = weights.get(target_lane, 1.0) + 2.0
        for lid in self.sd.lanes:
            if self.sd.lanes[lid].air: weights[lid] = weights.get(lid, 1.0) + 1.0
        best, bscore, bfacing = None, -1.0, "E"
        for t in self.sd.high_tiles:
            if t in self.occ: continue
            f, cov = best_facing(self.sd, t, tmpl, weights)
            if st["dmg"] == "heal":
                tiles = coverage_tiles(self.sd, t, f, tmpl)
                score = sum(2.0 for u in self.units if u.alive and u.tile in tiles and u.kind != "civilian") + 0.01 * sum(len(v) for v in cov.values())
            else:
                score = sum(weights[lid] * len(idxs) for lid, idxs in cov.items())
                for u in self.units:
                    if u.alive and u.is_ground and u.kind != "civilian":
                        for lid, idx in u.lanes.items():
                            if idx in cov.get(lid, ()): score += 3.0
            if score > bscore: best, bscore, bfacing = t, score, f
        if best is None: return None
        if self.rng.random() >= self.pol.get("post_quality", 1.0):
            best = self.rng.choice([t for t in self.sd.high_tiles if t not in self.occ])
            bfacing, _ = best_facing(self.sd, best, tmpl, weights)
        return (best, bfacing)

    def random_ground_post(self) -> tuple | None:
        c = [t for t in self.sd.ground_tiles if t not in self.occ]
        return self.rng.choice(c) if c else None

    # ---------- 정책
    def decide(self):
        pol = self.pol
        self.rule_retreat(pol); self.rule_skills(pol); self.rule_ult(pol); self.rule_relocate(pol); self.rule_deploy(pol)

    def rule_retreat(self, pol):
        if pol.get("retreat") != "low_hp": return
        thr = pol.get("retreat_hp", 0.2)
        for u in list(self.units):
            if u.kind != "legion" or not u.alive or u.hp > thr * u.max_hp: continue
            if u.is_ground:
                others = [b for lid in u.lanes for b in self.ground_blockers(lid) if b is not u]
                if u.blocked and not others: continue
            self.retreat(u)

    def skill_ready(self, u: Unit) -> bool:
        sk = u.st["skill"]
        return sk.get("mode") == "manual" and u.sp >= sk["sp"] and u.skill_t <= 0

    def skill_condition(self, u: Unit, mode: str) -> bool:
        cls = u.st["cls"]
        if mode == "when_ready":
            if cls == "medic": return any(a.alive and a.hp < a.max_hp and a.tile in u.cov_tiles for a in self.units)
            if cls == "shield": return len(u.blocked) >= 1
            return len(self.targets_ranged(u)) >= 1
        if mode == "smart":
            if cls == "shield": return len(u.blocked) >= 2 or (len(u.blocked) >= 1 and u.hp < 0.5 * u.max_hp)
            if cls == "medic": return any(a.alive and a.hp < 0.6 * a.max_hp and a.tile in u.cov_tiles for a in self.units)
            return len(self.targets_ranged(u)) >= 2
        if mode == "random":
            return self.rng.random() < self.pol.get("skill_prob", 0.5)
        return False

    def rule_skills(self, pol):
        mode = pol.get("skill", "auto_only")
        if mode == "auto_only": return
        for u in self.units:
            if u.kind not in ("legion", "npc") or not u.active or not self.skill_ready(u): continue
            if self.skill_condition(u, mode): self.use_skill(u)

    def use_skill(self, u: Unit):
        sk = u.st["skill"]; u.sp -= sk["sp"]; self.skill_uses += 1; m = u.st["skill_rank_mult"]
        if "dur" in sk: u.skill_t = sk["dur"]
        if sk.get("heal_pct"):
            for a in self.units:
                if a.alive and a.tile in u.cov_tiles and a.kind != "civilian":
                    a.hp = min(a.max_hp, a.hp + sk["heal_pct"] * m * a.max_hp)
        if sk.get("aoe_mult"):
            tg = self.targets_ranged(u)
            if tg:
                center = max(tg, key=lambda e: e.p)
                for e in self.lane_enemies(center.lane):
                    if abs(e.p - center.p) <= 1.0:
                        self.damage_enemy(e, eff_damage(u.st["atk"] * sk["aoe_mult"] * m, "arts", e.st["def"], e.st["res"], self.R["min_damage_ratio"]), u)

    def rule_ult(self, pol):
        mode = pol.get("ult", "never")
        if mode == "never" or not self.hero_present or not self.hero.active or not self.hero_stats.get("relocate"): return
        U = self.P["hero"]["ult_flash"]
        if self.hero.ult_sp < U["sp"]: return
        tg = self.hero_front_targets(U["tiles"])
        need = pol.get("ult_min_enemies", 1)
        weight = sum(3 if e.st["is_boss"] else 1 for e in tg)
        if tg and weight >= need:
            atk = self.hero_atk()
            for e in tg:
                self.damage_enemy(e, eff_damage(atk * U["atk_mult"], "phys", e.st["def"], e.st["res"], self.R["min_damage_ratio"]), self.hero)
                e.stun = max(e.stun, U["stun"])
            self.hero.ult_sp -= U["sp"]; self.ult_uses += 1

    def hero_front_targets(self, tiles: int) -> list[Enemy]:
        out = []
        for lid, idx in self.hero.lanes.items():
            for e in self.lane_enemies(lid):
                if idx - tiles <= e.p <= idx + 0.99: out.append(e)
        return out

    def rule_relocate(self, pol):
        mode = pol.get("relocate", "none")
        h = self.hero
        if mode == "rare" and self.tutorial_relocate and self.tutorial_relocate[0] <= self.t <= self.tutorial_relocate[1]:
            mode = "threat"   # 튜토리얼이 재배치를 강제 안내하는 구간
        if mode == "none" or not self.hero_present or not self.hero_stats.get("relocate") or not h.active or h.cd > 0: return
        best, bscore, bmax = None, 0.0, -1.0
        if mode in ("threat", "defensive"):
            for lid in self.sd.lanes:
                w, maxp = self.open_threat(lid)
                if w <= 0: continue
                if mode == "defensive" and (self.sd.lanes[lid].length - maxp) > pol.get("urgent_tiles", 6): continue
                if w > bscore: best, bscore, bmax = lid, w, maxp
            if best is None: return
            if best in h.lanes and bmax < h.lanes[best]: return   # 이미 그 길목에 서 있음
            # 현재 자리의 위협: 저지 중 + 4칸 안으로 다가온 적만 센다 (먼 적은 아직 위협이 아니다)
            here_w = sum(KIND_W[e.st["kind"]] for e in h.blocked) + sum(KIND_W[e.st["kind"]] for lid in h.lanes for e in self.lane_enemies(lid) if e.blocked_by is None and 0 <= h.lanes[lid] - e.p <= 4)
            L = self.sd.lanes[best].length
            imminent = bmax >= L - 5          # 5칸 안에 누수
            if not imminent:
                for lid in h.lanes:
                    others = [u for u in self.ground_blockers(lid) if u is not h]
                    if not others and (self.incoming_soon(lid, 12.0) > 0 or any(e.blocked_by is None for e in self.lane_enemies(lid) if not e.st["flying"])):
                        return   # 내 경로에 곧 적이 오는데 대신 막을 아군이 없다
            blocked_remaining = min((self.sd.lanes[lid].length - h.lanes[lid] for lid in h.lanes), default=99)
            if imminent and blocked_remaining >= 6:
                self.move_hero_to(best, bmax); return
            if here_w >= bscore: return
            self.move_hero_to(best, bmax)
        elif mode == "greedy_kill":
            counts = {lid: len(self.lane_enemies(lid)) for lid in self.sd.lanes}
            best = max(counts, key=counts.get)
            if counts[best] == 0: return
            here = max((counts[lid] for lid in h.lanes), default=0)
            if here >= counts[best]: return
            maxp = max(e.p for e in self.lane_enemies(best) if e.blocked_by is None) if any(e.blocked_by is None for e in self.lane_enemies(best)) else -1
            self.move_hero_to(best, maxp)
        elif mode == "rare":
            lanes = [lid for lid in self.sd.lanes if self.open_threat(lid)[0] > 0]
            if lanes and self.rng.random() < pol.get("relocate_prob", 0.2):
                lid = self.rng.choice(lanes)
                c = self.lane_ground_candidates(lid, hero=True)
                if c: self.move_hero_tile(self.rng.choice(c))

    def move_hero_to(self, lid: str, maxp: float):
        ln = self.sd.lanes[lid]
        cands = self.lane_ground_candidates(lid, hero=True, min_idx=maxp if maxp >= 0 else -1)
        if not cands: return
        want = min(ln.length - 1, int(max(maxp, 0)) + 2)
        shared = [t for t in cands if len(self.sd.lanes_at(t)) > 1]
        pool = shared if shared else cands
        tile = min(pool, key=lambda t: abs(ln.index_of[t] - want))
        if self.rng.random() >= self.pol.get("post_quality", 1.0): tile = self.rng.choice(cands)
        self.move_hero_tile(tile)

    def move_hero_tile(self, tile: tuple):
        h = self.hero
        for e in h.blocked: e.blocked_by = None
        h.blocked = []
        self.occ.pop(h.tile, None); h.tile = tile; self.occ[tile] = h
        h.lanes = self.sd.lanes_at(tile)
        h.moving = self.P["hero"]["relocate_time"]; h.cd = self.hero_stats["relocate_cd"]; self.relocates += 1

    def rule_deploy(self, pol):
        mode = pol.get("deploy", "none")
        if mode == "none" or not self.cards: return
        reserve = pol.get("dp_reserve", 0)
        avail = [c for c in self.cards if c.available]
        if not avail or self.deployed_legion() >= self.deploy_limit: return
        any_enemy = any(e.alive for e in self.enemies)
        if mode == "card_order_reactive":
            if not any_enemy: return
            lid = max(self.sd.lanes, key=lambda l: len(self.lane_enemies(l)))
            for c in avail:
                if self.dp >= c.current_cost(self.R["redeploy_mult"]):
                    self.try_deploy(c, lid); return
            return
        if mode == "dps_first":
            order = ["spear", "special", "sniper", "caster", "shield", "support", "medic"]
            lid = max(self.sd.lanes, key=lambda l: (len(self.lane_enemies(l)), self.incoming_soon(l, 15)))
            if not any_enemy and not pol.get("predeploy"): return
            for cls in order:
                for c in avail:
                    if c.st["cls"] == cls and self.dp >= c.current_cost(self.R["redeploy_mult"]) + (0 if cls in GROUND_ORDER else reserve):
                        self.try_deploy(c, lid); return
            return
        # priority (B · D · E)
        needs = []
        for lid in self.sd.lanes:
            if self.sd.lanes[lid].air: continue
            n_now = sum(1 for e in self.lane_enemies(lid) if not e.st["flying"])
            soon = self.incoming_soon(lid, 15.0) if pol.get("predeploy") else 0
            if (n_now + soon) == 0: continue
            if self.ground_blockers(lid): continue
            needs.append((self.open_threat(lid)[0], n_now + soon, lid))
        needs.sort(reverse=True)
        if needs:
            lid = needs[0][2]
            for cls in GROUND_ORDER:
                for c in avail:
                    if c.st["cls"] == cls and self.dp >= c.current_cost(self.R["redeploy_mult"]):
                        if self.try_deploy(c, lid): return
            return
        # 비행 적이 오는 레인에 대공 커버가 없으면 사수 우선
        air_lanes = [lid for lid in self.sd.lanes if (self.sd.lanes[lid].air or any(e.st["flying"] for e in self.lane_enemies(lid)) or self.incoming_flying(lid, 20.0))]
        for lid in air_lanes:
            if not any(u.alive and not u.is_ground and u.st["dmg"] in ("phys", "arts") and lid in u.cov for u in self.units):
                for cls in ("sniper", "caster", "support"):
                    for c in avail:
                        if c.st["cls"] == cls and self.dp >= c.current_cost(self.R["redeploy_mult"]):
                            if self.try_deploy(c, lid): return
        # 사격 커버가 없는 저지 포스트
        for cls in RANGED_ORDER:
            for c in avail:
                if c.st["cls"] != cls or self.dp < c.current_cost(self.R["redeploy_mult"]) + reserve: continue
                uncovered = [lid for u in self.units if u.alive and u.is_ground and u.kind != "civilian" for lid, idx in u.lanes.items() if self.ranged_cov_at(lid, idx) == 0]
                if uncovered:
                    if self.try_deploy(c, uncovered[0]): return
        for c in avail:
            if c.st["cls"] == "medic" and self.dp >= c.current_cost(self.R["redeploy_mult"]) + reserve and sum(1 for u in self.units if u.alive and u.is_ground and u.kind != "civilian") >= 2:
                if self.try_deploy(c, None): return
        for c in avail:
            if c.st["cls"] == "support" and self.dp >= c.current_cost(self.R["redeploy_mult"]) + reserve and any_enemy:
                if self.try_deploy(c, max(self.sd.lanes, key=lambda l: len(self.lane_enemies(l)))): return
        # 곧(40s) 적이 올 레인에 저지가 없으면 DP를 아낀다 (추가 소집 금지)
        if pol.get("predeploy"):
            for lid in self.sd.lanes:
                if self.sd.lanes[lid].air: continue   # 비행 경로는 저지 대상이 아니다
                if self.incoming_soon(lid, 40.0) > 0 and not self.ground_blockers(lid):
                    return
        # 여유 DP → 저지가 가장 얇은 레인(주인공이 선 레인은 후순위)에 추가 저지
        if any_enemy:
            def thin(l):
                blockers = [u for u in self.ground_blockers(l) if u.kind != "hero"]
                hero_here = self.hero_present and l in self.hero.lanes
                return (len(blockers) + (1 if hero_here else 0), -self.incoming_soon(l, 60.0), -len(self.lane_enemies(l)))
            lid = min(self.sd.lanes, key=thin)
            for cls in GROUND_ORDER + RANGED_ORDER:
                for c in avail:
                    if c.st["cls"] == cls and self.dp >= c.current_cost(self.R["redeploy_mult"]) + reserve:
                        if self.try_deploy(c, lid): return

    def try_deploy(self, card: Card, lid: str | None) -> bool:
        st = card.st
        if self.rng.random() < self.pol.get("mistake", 0.0):
            if st["pos"] == "G":
                t = self.random_ground_post(); return bool(t) and self.deploy_card(card, t, "E")
            free = [t for t in self.sd.high_tiles if t not in self.occ]
            if not free: return False
            t = self.rng.choice(free); f, _ = best_facing(self.sd, t, self.P["ranges"][st["range"]])
            return self.deploy_card(card, t, f)
        if st["pos"] == "G":
            lane = lid or max(self.sd.lanes, key=lambda l: len(self.lane_enemies(l)))
            t = self.best_ground_post(lane, hero=False)
            return bool(t) and self.deploy_card(card, t, "E")
        r = self.best_high_post(st, lid)
        return bool(r) and self.deploy_card(card, r[0], r[1])

    # ---------- 전투
    def hero_atk(self) -> float:
        return self.hero_stats["atk"] * (1.0 + self.P["hero"]["momentum"]["per_stack_atk"] * self.hero.momentum)

    def targets_ranged(self, u: Unit) -> list[Enemy]:
        out = []
        for lid, idxs in u.cov.items():
            for e in self.lane_enemies(lid):
                if int(e.p) in idxs or (e.blocked_by is not None and int(e.p) in idxs):
                    if e.st["stealth"] and e.blocked_by is None: continue
                    if e.st["flying"] and u.is_ground: continue
                    out.append(e)
        return out

    def damage_enemy(self, e: Enemy, dmg: float, src: Unit):
        if not e.alive or e.invuln > 0: return
        e.hp -= dmg
        if e.hp <= 0:
            if e.st["revive"] and not e.revived:
                e.revived = True; e.hp = 0.5 * e.st["hp"]; return
            self.kill(e, src)

    def kill(self, e: Enemy, src: Unit):
        e.alive = False
        if e.blocked_by is not None and e in e.blocked_by.blocked: e.blocked_by.blocked.remove(e)
        self.kills += 1; kind = e.st["kind"]
        if self.hero_present: self.hero.ult_sp += self.R["sp_per_kill"][kind]
        if src is not None and src is self.hero:
            self.hero_kills += 1
            gain = self.R["hero_kill_dp"][kind] * self.hero_stats.get("cmd_dp", 1.0) * self.ov.get("hero_kill_dp_mult", 1.0)
            self.dp = min(self.R["dp_cap"], self.dp + gain); self.dp_earned_kill += gain
            if self.hero_stats.get("momentum_max", 0):
                self.hero.momentum = min(self.hero_stats["momentum_max"], self.hero.momentum + 1); self.hero.last_kill_t = self.t
            if self.hero_stats.get("kill_heal"): self.hero.hp = min(self.hero.max_hp, self.hero.hp + self.hero_stats["kill_heal"] * self.hero.max_hp)

    def ally_attacks(self):
        dt = self.dt; mr = self.R["min_damage_ratio"]
        for u in list(self.units):
            if not u.active or u.kind == "civilian": continue
            sk = u.st["skill"]
            if u.kind == "hero":
                front = self.hero_stats["range_front"]; idxs = {}
                tg = []
                for lid, idx in u.lanes.items():
                    for e in self.lane_enemies(lid):
                        if e.st["flying"]: continue
                        if idx - front <= e.p <= idx + 0.99: tg.append(e)
                tg.sort(key=lambda e: (e.blocked_by is not u, -e.p))
                tg = tg[: self.hero_stats["max_targets"]]
                if not tg: continue
                interval = self.hero_stats["interval"] * (1.0 - self.P["hero"]["momentum"]["per_stack_speed"] * u.momentum)
                per = dt / max(0.2, interval); atk = self.hero_atk()
                for e in tg:
                    self.damage_enemy(e, eff_damage(atk, "phys", e.st["def"], e.st["res"], mr) * per, u)
                continue
            interval = u.st["interval"]
            if u.skill_t > 0 and sk.get("interval_mult"): interval *= sk["interval_mult"]
            per = dt / interval
            atk = u.st["atk"]
            if u.skill_t > 0 and sk.get("atk_mult") and sk.get("mode") == "passive": atk *= sk["atk_mult"]
            if u.st["dmg"] == "heal":
                cands = [a for a in self.units if a.alive and a.kind != "civilian" and a.hp < a.max_hp and a.tile in u.cov_tiles]
                if cands:
                    a = min(cands, key=lambda a: a.hp / a.max_hp); a.hp = min(a.max_hp, a.hp + atk * per)
                continue
            if u.is_ground:
                tg = list(u.blocked)
                if not tg:
                    for lid, idx in u.lanes.items():
                        for e in self.lane_enemies(lid):
                            if not e.st["flying"] and e.blocked_by is None and idx - 1 <= e.p <= idx + 0.99: tg.append(e)
                if not tg: continue
                e = max(tg, key=lambda e: e.p)
                dmg = eff_damage(atk, u.st["dmg"], e.st["def"], e.st["res"], mr) * per
                if sk.get("charge") == "attack":
                    u.sp += per * self.R["attack_sp_per_hit"]
                    if u.sp >= sk["sp"]:
                        u.sp -= sk["sp"]; dmg += eff_damage(atk * sk.get("bonus_mult", 1.5) * u.st["skill_rank_mult"], u.st["dmg"], e.st["def"], e.st["res"], mr)
                self.damage_enemy(e, dmg, u)
            else:
                tg = self.targets_ranged(u)
                if not tg: continue
                if u.st.get("prio") == "flying" and any(e.st["flying"] for e in tg): tg = [e for e in tg if e.st["flying"]]
                e = max(tg, key=lambda e: e.p)
                self.damage_enemy(e, eff_damage(atk, u.st["dmg"], e.st["def"], e.st["res"], mr) * per, u)
                if u.st.get("slow"):
                    s = u.st["slow"] + (sk.get("slow", 0) if u.skill_t > 0 else 0)
                    for x in tg: x.slow = max(x.slow, s)

    def enemy_attacks(self):
        dt = self.dt; mr = self.R["min_damage_ratio"]; ivl = self.P["enemies"]["attack_interval"]
        for e in self.enemies:
            if not e.alive or e.stun > 0: continue
            dtype = "arts" if e.st["arts"] else "phys"
            target = None
            if e.blocked_by is not None:
                target = e.blocked_by
            elif e.st["ranged"] > 0:
                best = None
                for u in self.units:
                    if not u.alive or u.kd > 0 or u.kind == "civilian": continue
                    if u.is_ground:
                        idx = u.lanes.get(e.lane)
                        if idx is not None and e.p <= idx <= e.p + e.st["ranged"]:
                            d = idx - e.p
                            if best is None or d < best[0]: best = (d, u)
                    else:
                        if e.lane in u.cov and int(e.p) in u.cov[e.lane] and e.st["ranged"] >= 2:
                            d = 1.5
                            if best is None or d < best[0]: best = (d, u)
                target = best[1] if best else None
            if target is not None:
                dmg = eff_damage(e.st["atk"], dtype, target.def_eff(), target.st["res"], mr) * dt / (e.st.get("interval", 1.0) * ivl)
                if e.charge_pending and e.blocked_by is target:
                    dmg += eff_damage(e.st["atk"], dtype, target.def_eff(), target.st["res"], mr); e.charge_pending = False
                self.damage_unit(target, dmg)
            if self.P["enemies"]["civilian_attack"]:
                for c in self.npcs.values():
                    if c.kind == "civilian" and c.alive and e.lane in c.lanes and int(e.p) == c.lanes[e.lane]:
                        c.hp -= e.st["atk"] * dt / ivl
                        if c.hp <= 0: c.alive = False; self.occ.pop(c.tile, None)

    def damage_unit(self, u: Unit, dmg: float):
        if not u.alive or u.kd > 0: return
        u.hp -= dmg
        if u.hp > 0: return
        if u.kind == "hero":
            u.kd = self.hero_stats["knockdown"]; self.knockdowns += 1; u.momentum = 0
            for e in u.blocked: e.blocked_by = None
            u.blocked = []
        elif u.kind == "npc":
            u.kd = 10.0; u.down_count += 1
            for e in u.blocked: e.blocked_by = None
            u.blocked = []
        else:
            self.legion_deaths += 1; card = u.card
            self.remove_unit(u); card.unit = None
            card.cooldown = card.st["redeploy"] * self.R["death_cooldown_mult"]

    # ---------- 진행
    def step(self):
        dt = self.dt; sd = self.sd
        # 스크립트
        for s in self.scripts:
            if s.get("t", -1) is not None and abs(s["t"] - self.t) < dt / 2:
                u = self.npcs.get(s.get("unit"))
                if u and u.alive: self.damage_unit(u, u.hp + 1)
        # 결정
        if self.t >= self.next_decision:
            self.decide(); self.next_decision = self.t + self.pol.get("decision_interval", 1.0)
        # 자원
        self.dp = min(self.R["dp_cap"], self.dp + self.dp_regen * dt)
        for c in self.cards:
            if c.cooldown > 0: c.cooldown = max(0.0, c.cooldown - dt)
        # 스폰
        while self.spawn_i < len(self.spawn_q) and self.spawn_q[self.spawn_i][0] <= self.t + 1e-9:
            _, eid, lane = self.spawn_q[self.spawn_i]; self.spawn_i += 1
            self.uid_seq += 1
            self.enemies.append(Enemy(build_enemy_stats(self.table, eid, sd.scale, self.ov), lane, self.uid_seq)); self.spawned += 1
        # 보스 페이즈
        self.update_boss()
        # 이동 · 저지
        for e in self.enemies:
            if not e.alive: continue
            if e.stun > 0: e.stun = max(0.0, e.stun - dt); continue
            if e.blocked_by is not None: continue
            prev = e.p
            code_here = sd.tile(*sd.lanes[e.lane].tiles[min(int(prev), sd.lanes[e.lane].length)])
            accel = 1.5 if (code_here == "A" and not e.st["flying"]) else 1.0
            e.p += e.st["speed"] * e.st.get("enrage", 1.0) * accel * (1.0 - e.slow) * dt; e.slow = 0.0   # 저지되지 않은 동안만 광폭화 배율
            L = sd.lanes[e.lane].length
            if not e.st["flying"] and not sd.lanes[e.lane].air:
                # 함정 타일: 처음 밟는 적에게 고정 피해 1회
                for ti in range(int(prev) + 1, min(int(e.p), L) + 1):
                    tl = sd.lanes[e.lane].tiles[ti]
                    if sd.tile(*tl) == "T" and tl not in self.traps_used:
                        self.traps_used.add(tl); self.damage_enemy(e, 300.0 * sd.scale.get("hp", 1.0), self.hero if self.hero_present else None)
                        if not e.alive: break
                if not e.alive: continue
                blockers = sorted((u for u in self.ground_blockers(e.lane)), key=lambda u: u.lanes[e.lane])
                for u in blockers:
                    idx = u.lanes[e.lane]
                    if prev < idx <= e.p and u.free_slots() > 0:
                        e.blocked_by = u; u.blocked.append(e); e.p = float(idx); break
                    if prev < idx <= e.p and u.free_slots() <= 0:
                        continue
            if e.blocked_by is None and e.p >= L:
                e.alive = False; self.leaks += 1; self.leak_log.append((round(self.t, 1), e.lane, e.st["id"]))
                if e.st["is_boss"]: self.lives = 0; self.fail = "boss"
                else: self.lives -= 1
        # 전투
        self.ally_attacks(); self.enemy_attacks()
        # 타이머
        for u in list(self.units):
            if u.kd > 0:
                u.kd -= dt
                if u.kd <= 0:
                    u.kd = 0.0; u.hp = (self.hero_stats["revive_hp"] if u.kind == "hero" else 0.3) * u.max_hp
                    if u.kind == "hero": u.cd = 0.0
            if u.moving > 0: u.moving = max(0.0, u.moving - dt)
            if u.cd > 0: u.cd = max(0.0, u.cd - dt)
            if u.skill_t > 0: u.skill_t = max(0.0, u.skill_t - dt)
            sk = u.st.get("skill", {})
            if sk.get("charge") == "natural" and u.active: u.sp = min(sk["sp"], u.sp + self.R["natural_sp_per_s"] * dt)
        for u in self.units:
            if u.alive and u.kd <= 0 and sd.tile(*u.tile) == "R" and u.hp < u.max_hp:
                u.hp = min(u.max_hp, u.hp + 0.02 * u.max_hp * dt)
        h = self.hero
        if self.hero_present and h.momentum > 0:
            M = self.P["hero"]["momentum"]
            if self.t - h.last_kill_t >= M["decay_after"]:
                h.momentum -= 1; h.last_kill_t = self.t - M["decay_after"] + M["decay_every"]
        for e in self.enemies:
            if e.invuln > 0: e.invuln = max(0.0, e.invuln - dt)
        self.enemies = [e for e in self.enemies if e.alive]
        self.t += dt

    def update_boss(self):
        b = self.sd.boss
        if not b: return
        boss = next((e for e in self.enemies if e.alive and e.st["is_boss"]), None)
        if boss is None: return
        frac = boss.hp / boss.st["hp"]
        phase = 0
        for i, ph in enumerate(b["phases"]):
            if frac <= ph["hp_above"] + 1e-9 and i + 1 < len(b["phases"]): continue
            if frac > ph["hp_above"]: phase = i; break
        if phase != self.boss_phase:
            first = self.boss_phase < 0
            self.boss_phase = phase; ph = b["phases"][phase]
            self.sealed = {tuple(t) for t in ph["sealed"]}
            if "invuln_2s" in ph.get("on_enter", []): boss.invuln = 2.0
            if "def_mult" in ph: boss.st["def"] = boss.st["def"] / boss.st.get("def_mult", 1.0) * ph["def_mult"]; boss.st["def_mult"] = ph["def_mult"]
            if "base_speed" not in boss.st: boss.st["base_speed"] = boss.st["speed"]
            boss.st["speed"] = boss.st["base_speed"] * ph.get("speed_mult", 1.0)   # 비행 선회 등
            if "flying" in ph:
                boss.st["flying"] = bool(ph["flying"])
                if boss.st["flying"] and boss.blocked_by is not None:
                    boss.blocked_by.blocked.remove(boss); boss.blocked_by = None
            if not first and self.hero_present: self.hero.ult_sp += self.R["sp_per_kill"]["boss"]   # 페이즈 전환 SP +5
            if self.hero_present and self.hero.tile in self.sealed:
                c = self.lane_ground_candidates(next(iter(self.hero.lanes)) if self.hero.lanes else "A", hero=True)
                if c:
                    tile = min(c, key=lambda t: abs(t[0] - self.hero.tile[0]) + abs(t[1] - self.hero.tile[1]))
                    cd = self.hero.cd; self.move_hero_tile(tile); self.hero.cd = cd; self.relocates -= 1

    def run(self) -> dict:
        self.setup()
        grace = self.P["sim"]["end_grace"]
        while True:
            self.step()
            if self.lives <= 0:
                self.fail = self.fail or "leak"; break
            if self.spawn_i >= len(self.spawn_q) and not self.enemies: break
            if self.t > self.last_spawn + grace:
                self.fail = "timeout"; break
        cleared = self.fail is None
        civ_alive = all(c.alive for c in self.npcs.values() if c.kind == "civilian") if any(c.kind == "civilian" for c in self.npcs.values()) else None
        return dict(cleared=cleared, star3=cleared and self.leaks == 0 and self.knockdowns == 0, leaks=self.leaks,
                    knockdowns=self.knockdowns, legion_deaths=self.legion_deaths, relocates=self.relocates, ult_uses=self.ult_uses,
                    hero_kills=self.hero_kills, kills=self.kills, dp_spent=self.dp_spent, dp_kill=self.dp_earned_kill,
                    deploys=self.deploys, retreats=self.retreats, skill_uses=self.skill_uses, time=self.t, fail=self.fail or "",
                    civ_alive=civ_alive, lives_left=max(0, self.lives))


def simulate_cell(sd: StageDef, P: dict, pol: dict, growth: dict, table: dict, runs: int, seed: int, ov: dict | None = None,
                  squad: dict | None = None) -> dict:
    rows = [Sim(sd, P, pol, growth, table, seed + i, ov, squad).run() for i in range(runs)]
    n = len(rows)
    def mean(k): return sum((r[k] or 0) for r in rows) / n
    out = dict(runs=n, P_clear=mean("cleared"), P_star3=mean("star3"), leaks=mean("leaks"), knockdowns=mean("knockdowns"),
               legion_deaths=mean("legion_deaths"), relocates=mean("relocates"), ult_uses=mean("ult_uses"),
               hero_kill_share=(sum(r["hero_kills"] for r in rows) / max(1, sum(r["kills"] for r in rows))),
               dp_spent=mean("dp_spent"), dp_kill=mean("dp_kill"), deploys=mean("deploys"), retreats=mean("retreats"),
               skill_uses=mean("skill_uses"), T_mean=mean("time"), lives_left=mean("lives_left"),
               cause_leak=sum(1 for r in rows if r["fail"] == "leak") / n, cause_boss=sum(1 for r in rows if r["fail"] == "boss") / n,
               cause_timeout=sum(1 for r in rows if r["fail"] == "timeout") / n)
    civ = [r["civ_alive"] for r in rows if r["civ_alive"] is not None]
    out["civ_alive"] = (sum(civ) / len(civ)) if civ else None
    return out
