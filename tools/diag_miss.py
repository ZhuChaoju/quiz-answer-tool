# -*- coding: utf-8 -*-
"""诊断当前未命中题目：输出每个选项的哈希距离与全库最近邻。"""
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from PIL import Image

from quiz_answer_tool import screen
from quiz_answer_tool.activities import load_modules
from quiz_answer_tool.activities.icon import hamming, icon_hash, locate_icon, option_candidates

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

sources = [s for s in screen.list_sources() if s.kind == "window" and "ONLINE" in s.name.upper()]
frame, _ = screen.capture(sources[0])
frame.save(r"D:\work\_downloads\miss_frame.png")

mods = {m.id: m for m in load_modules(os.path.join(ROOT, "banks"))}
mod = mods["teachers"]
box = locate_icon(frame, mod.rois["search"].__dict__, mod.panel_bg)
print("icon box:", box)
if box is None:
    sys.exit("icon not located")

h = icon_hash(frame.crop(box))
print("live hash:", h)

# 选项 OCR
from quiz_answer_tool import ocr
o_crop = mod.rois["option"].crop(frame, pad=0.02)
o_lines = ocr.recognize(o_crop, "ch", 0.4, "tiny", True, False)
cands = option_candidates(o_lines)
print("option candidates:", [c[0] for c in cands])

for name, ln, left, right in cands:
    lib_h = mod.bank.hash_of(name)
    tag = "exact"
    if lib_h is None:
        fname = mod.bank.fuzzy_name(name)
        if fname:
            lib_h = mod.bank.hash_of(fname)
            tag = f"fuzzy->{fname}"
    if lib_h is None:
        print(f"  {name}: 库中无此条目")
        continue
    print(f"  {name} [{tag}]: 距离 {hamming(h, lib_h)}")

near = mod.bank.nearest(h)
print("全库最近邻:", near)
