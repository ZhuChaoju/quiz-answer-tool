# -*- coding: utf-8 -*-
import json

p = r"D:\work\quiz-answer-tool\dist\release\config.json"
d = json.load(open(p, encoding="utf-8-sig"))
d["ui"]["autostart"] = False
json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("autostart off for this launch")
