# -*- coding: utf-8 -*-
import json
import shutil

p = r"banks\teachers\module.json"
d = json.load(open(p, encoding="utf-8-sig"))
d["option_max_distance"] = 104
json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
shutil.copyfile(p, r"dist\release\banks\teachers\module.json")
print("option_max_distance =", d["option_max_distance"], "| synced")
