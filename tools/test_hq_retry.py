# -*- coding: utf-8 -*-
"""验证 HQ 重识别：tiny 漏读的单个数字选项，small 引擎能否读出并定位红框。"""
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from quiz_answer_tool.activities import load_modules
from quiz_answer_tool.activities.text import find_answer_line
from quiz_answer_tool import ocr, screen

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

src = screen.find_game_source("梦幻西游")
frame, _ = screen.capture(src)
mods = {m.id: m for m in load_modules(os.path.join(ROOT, "banks"))}
mod = mods["keju_xiangshi"]
o_crop = mod.rois["option"].crop(frame, pad=0.02)

lines_tiny = ocr.recognize(o_crop, "ch", 0.4, "tiny", True, False, mod.merge_threshold)
print("tiny:", [(ln.text, [t for t, _, _ in ln.segments]) for ln in lines_tiny])

lines_small = ocr.recognize_hq(o_crop, "ch", 0.3, False, mod.merge_threshold)
print("small:", [(ln.text, [t for t, _, _ in ln.segments]) for ln in lines_small])

al = find_answer_line(lines_small, "1", fuzzy_box_threshold=50)
print("find '1' (fuzzy50):", al)
al = find_answer_line(lines_small, "1", fuzzy_box_threshold=70)
print("find '1' (fuzzy70):", al)
