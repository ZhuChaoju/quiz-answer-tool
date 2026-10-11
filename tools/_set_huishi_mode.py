# -*- coding: utf-8 -*-
import json

p = r"D:\work\quiz-answer-tool\dist\release\config.json"
d = json.load(open(p, encoding="utf-8-sig"))
d["ui"]["autostart"] = True
d["ui"]["module"] = "keju_huishi"
json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("autostart=on, module=keju_huishi (科举·会试)")
