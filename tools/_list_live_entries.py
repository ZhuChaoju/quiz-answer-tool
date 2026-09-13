# -*- coding: utf-8 -*-
import io
import sys
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import json

entries = json.load(open(r"dist\release\banks\teachers\icons.json", encoding="utf-8-sig"))
print("总条目:", len(entries))
names = [e["name"] for e in entries]
dup_names = {n: c for n, c in Counter(names).items() if c > 1}
print("同名多条:", dup_names)
# 找今晚录入的（哈希不在官方素材重算集里的）
import sys as _s
_s.path.insert(0, r"D:\work\quiz-answer-tool\src")
from quiz_answer_tool.activities.icon import icon_hash
import os

ICON_DIR = r"D:\work\quiz-answer-tool\banks\teachers\icons"
asset_hash = {}
for fn in os.listdir(ICON_DIR):
    if fn.endswith(".png"):
        from PIL import Image

        asset_hash[os.path.splitext(fn)[0]] = icon_hash(Image.open(os.path.join(ICON_DIR, fn)))
live_entries = []
for e in entries:
    ah = asset_hash.get(e["name"])
    if ah is None or e["hash"] != ah:
        live_entries.append(e)
print("\n实拍录入条目（哈希与官方素材不同）:")
for e in live_entries:
    print("  ", e["name"], e["hash"][:16])
