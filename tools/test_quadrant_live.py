# -*- coding: utf-8 -*-
"""端到端验证：当前题目 → 象限兜底 → 红框象限。"""
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from quiz_answer_tool.activities import load_modules
from quiz_answer_tool import screen

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OCR_CFG = {"model_type": "tiny", "lang": "ch", "confidence": 0.4, "use_dml": False}

src = screen.find_game_source("梦幻西游")
frame, _ = screen.capture(src)
mods = {m.id: m for m in load_modules(os.path.join(ROOT, "banks"))}
mod = mods["keju_xiangshi"]
r = mod.recognize(frame, OCR_CFG)
print("答案:", r.answer or "未命中", "| state:", r.state, "| note:", r.note)
if r.answer_line:
    ln, sx1, sx2 = r.answer_line
    rl, rt, rr, rb = mod.rois["option"].rect_px(frame.size, 0.02)
    print(f"红框像素: x {rl + sx1:.0f} ~ {rl + sx2:.0f}, y中心 {rt + ln.center_y:.0f}")
    from PIL import ImageDraw

    img = frame.copy()
    d = ImageDraw.Draw(img)
    d.rectangle((rl + sx1 - 4, rt + ln.center_y - ln.height / 2 - 2,
                 rl + sx2 + 4, rt + ln.center_y + ln.height / 2 + 2), outline=(255, 0, 0), width=3)
    crop = img.crop((350, 480, 1150, 780))
    crop.save(r"D:\work\_downloads\quadrant_check.png")
    print("saved quadrant_check.png")
