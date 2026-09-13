# -*- coding: utf-8 -*-
"""测试：选项区放大 2x 后 HQ 识别能否读出漏掉的第二行选项。"""
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from quiz_answer_tool.activities import load_modules
from quiz_answer_tool import ocr, screen

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

src = screen.find_game_source("梦幻西游")
frame, _ = screen.capture(src)
mods = {m.id: m for m in load_modules(os.path.join(ROOT, "banks"))}
mod = mods["keju_xiangshi"]
o_crop = mod.rois["option"].crop(frame, pad=0.02)

big = o_crop.resize((o_crop.width * 2, o_crop.height * 2), o_crop.resize.__self__.Resampling if False else 2)
lines = ocr.recognize_hq(big, "ch", 0.3, False, mod.merge_threshold)
print("2x+small:", [(ln.text, round(ln.center_y)) for ln in lines])
lines2 = ocr.recognize_hq(big, "ch", 0.2, False, mod.merge_threshold)
print("2x+small conf0.2:", [(ln.text, round(ln.center_y)) for ln in lines2])
