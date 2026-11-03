#!/usr/bin/env python3
"""unity/Data/Stages/*.json → unity/Data/StageIndex.json (챕터별 목록)."""
import glob, json, os
ROOT = os.path.join(os.path.dirname(__file__), "..", "unity", "Data")
items = []
for p in glob.glob(os.path.join(ROOT, "Stages", "Stage_*.json")):
    s = json.load(open(p, encoding="utf-8"))
    items.append({"id": s["id"], "chapter": s["chapter"], "name": s["name"], "file": os.path.basename(p), "enemy_total": s["enemy_total"],
                  "lives": s["lives"], "deploy_limit": s["deploy_limit"], "routes": len(s["routes"]), "routes_air": len(s.get("routes_air", {})),
                  "boss": (s.get("boss") or {}).get("id")})
items.sort(key=lambda z: (z["chapter"], z["id"].startswith("SC"), [int(v) if v.isdigit() else v for v in z["id"].split("-")]))
json.dump({"stages": items}, open(os.path.join(ROOT, "StageIndex.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"index: {len(items)} stages")
