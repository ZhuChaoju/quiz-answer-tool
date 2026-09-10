# -*- coding: utf-8 -*-
"""解耦实证：修改 banks/keju 模块的 merge_threshold 只影响科举，教师节不受影响。"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from quiz_answer_tool.activities import load_modules

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
keju_json = os.path.join(ROOT, "banks", "keju", "modules", "keju_huishi.json")

# 1) 改成极端值 0.2
data = json.load(open(keju_json, encoding="utf-8-sig"))
data["merge_threshold"] = 0.2
json.dump(data, open(keju_json, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

mods = {m.id: m for m in load_modules(os.path.join(ROOT, "banks"))}
k, t = mods["keju_huishi"], mods["teachers"]
ok1 = abs(k.merge_threshold - 0.2) < 1e-9
ok2 = abs(t.merge_threshold - 0.5) < 1e-9
print(f"keju merge_threshold={k.merge_threshold} (期望 0.2) {'OK' if ok1 else 'FAIL'}")
print(f"teachers merge_threshold={t.merge_threshold} (期望 0.5，不受影响) {'OK' if ok2 else 'FAIL'}")

# 2) 还原
data["merge_threshold"] = 0.6
json.dump(data, open(keju_json, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
mods = {m.id: m for m in load_modules(os.path.join(ROOT, "banks"))}
ok3 = abs(mods["keju_huishi"].merge_threshold - 0.6) < 1e-9
print(f"还原后 keju={mods['keju_huishi'].merge_threshold} {'OK' if ok3 else 'FAIL'}")

sys.exit(0 if (ok1 and ok2 and ok3) else 1)
