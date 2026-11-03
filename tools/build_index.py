# 生成 data/index.json：33 篇的目录（篇名、部分、简介、各段小标题、字数、是否已做好）
import json, glob, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
ROOT = os.path.join(os.path.dirname(__file__), "..", "data")
from chapters import CH  # noqa: E402

out = []
for n, cid, _, title, part in CH:
    key = f"{n:02d}-{cid}"
    src = open(os.path.join(ROOT, "src", key + ".txt"), encoding="utf-8").read()
    item = {"key": key, "n": n, "id": cid, "title": title, "part": part,
            "chars": len(re.sub(r"[^一-鿿]", "", src)), "ready": False}
    p = os.path.join(ROOT, key + ".json")
    if os.path.exists(p):
        d = json.load(open(p, encoding="utf-8"))
        item.update(ready=True, intro=d["intro"],
                    sections=[{"title": s["title"], **({"illustrated": s["illustrated"]} if s.get("illustrated") else {})}
                              for s in d["sections"]])
    out.append(item)
json.dump(out, open(os.path.join(ROOT, "index.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("ready", sum(o["ready"] for o in out), "/", len(out))
