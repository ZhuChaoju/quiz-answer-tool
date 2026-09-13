# -*- coding: utf-8 -*-
import json

p = r"banks\keju\modules\keju_xiangshi.json"
d = json.load(open(p, encoding="utf-8-sig"))
d["presence_min_lum"] = 88
json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("xiangshi presence_min_lum=88 saved")
