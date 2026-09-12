# -*- coding: utf-8 -*-
import json

p = r"D:\work\quiz-answer-tool\dist\release\config.json"
d = json.load(open(p, encoding="utf-8-sig"))
d["ui"]["overlay"] = True
d["ui"]["locked"] = {"teachers": True, "keju_huishi": True}
json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("overlay restored, teachers locked")
