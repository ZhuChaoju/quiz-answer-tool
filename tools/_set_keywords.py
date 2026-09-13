# -*- coding: utf-8 -*-
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import json

# 各模块的题目关键词（出现在题面/标题的可靠词）
cfgs = {
    r"banks\keju\modules\keju.json": ["御前科举", "礼部考题", "答对", "题目"],
    r"banks\teachers\module.json": ["技能或法术名称", "请指出下图"],
    r"banks\yuanxiao\module.json": ["灯谜"],
}
for p, kws in cfgs.items():
    d = json.load(open(p, encoding="utf-8-sig"))
    d["gate_keywords"] = kws
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(p, "->", kws)

import shutil

shutil.copyfile(r"banks\keju\modules\keju.json", r"dist\release\banks\keju\modules\keju.json")
shutil.copyfile(r"banks\teachers\module.json", r"dist\release\banks\teachers\module.json")
shutil.copyfile(r"banks\yuanxiao\module.json", r"dist\release\banks\yuanxiao\module.json")
print("release banks synced")
