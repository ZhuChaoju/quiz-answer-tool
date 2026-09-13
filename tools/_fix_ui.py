# -*- coding: utf-8 -*-
import json

p = r"D:\work\quiz-answer-tool\dist\release\config.json"
d = json.load(open(p, encoding="utf-8-sig"))
d["ui"]["overlay"] = True
d["ui"].setdefault("locked", {})
d["ui"]["locked"]["teachers"] = True
json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("overlay:", d["ui"]["overlay"], "| locked.teachers:", d["ui"]["locked"].get("teachers"))
