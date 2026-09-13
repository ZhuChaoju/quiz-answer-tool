# -*- coding: utf-8 -*-
"""诊断当前题目的选项 OCR 行结构 + find_answer_line 匹配过程。"""
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from PIL import Image

from quiz_answer_tool.activities import load_modules
from quiz_answer_tool.activities.text import find_answer_line
from quiz_answer_tool import ocr, screen

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

src = screen.find_game_source("梦幻西游")
frame, _ = screen.capture(src)
frame.save(r"D:\work\_downloads\diag_frame.png")
print("frame:", frame.size)

mods = {m.id: m for m in load_modules(os.path.join(ROOT, "banks"))}
for mid in ("keju_xiangshi", "keju_huishi"):
    mod = mods[mid]
    o_crop = mod.rois["option"].crop(frame, pad=0.02)
    o_lines = ocr.recognize(o_crop, "ch", 0.4, "tiny", True, False, mod.merge_threshold)
    print(f"\n== {mid} 选项区 OCR ==")
    for ln in o_lines:
        segs = [(t, round(a), round(b)) for t, a, b in ln.segments]
        print(f"  y={ln.center_y:.0f} h={ln.height:.0f} text={ln.text!r} segs={segs}")
    ans = "10两/件"
    al = find_answer_line(o_lines, ans)
    print(f"  find_answer_line(10两/件) -> {al}")
    if al:
        ln, sx1, sx2 = al
        rl, rt, rr, rb = mod.rois["option"].rect_px(frame.size, 0.02)
        print(f"  红框像素: x {rl + sx1:.0f} ~ {rl + sx2:.0f}, y {rt + ln.center_y:.0f}")
