# -*- coding: utf-8 -*-
"""离线验证实况帧：红框像素位置 vs 选项 A 真实位置。"""
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from PIL import Image

from quiz_answer_tool.activities import load_modules

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OCR_CFG = {"model_type": "tiny", "lang": "ch", "confidence": 0.4, "use_dml": False}
OPTION_PAD = 0.02

frame = Image.open(r"D:\work\_downloads\live_now.png").convert("RGB")
mods = {m.id: m for m in load_modules(os.path.join(ROOT, "banks"))}
mod = mods["teachers"]
r = mod.recognize(frame, OCR_CFG)
print("answer:", r.answer, "| note:", r.note, "| located:", r.answer_line is not None)

if r.answer_line:
    line, sx1, sx2 = r.answer_line
    size = frame.size
    rl, rt, rr, rb = mod.rois["option"].rect_px(size, OPTION_PAD)
    x1 = rl + sx1
    x2 = rl + sx2
    y1 = rt + line.center_y - line.height / 2
    y2 = rt + line.center_y + line.height / 2
    print(f"answer box px: ({x1:.0f},{y1:.0f})-({x2:.0f},{y2:.0f})")
    print("expect option A ~ (407,427)-(590,475)")

# 在帧上画出红框存图目测
if r.answer_line:
    line, sx1, sx2 = r.answer_line
    size = frame.size
    rl, rt, rr, rb = mod.rois["option"].rect_px(size, OPTION_PAD)
    x1 = rl + sx1 - 4
    x2 = rl + sx2 + 4
    y1 = rt + line.center_y - line.height / 2 - 2
    y2 = rt + line.center_y + line.height / 2 + 2
    img = frame.copy()
    from PIL import ImageDraw

    d = ImageDraw.Draw(img)
    d.rectangle((x1, y1, x2, y2), outline=(255, 0, 0), width=3)
    crop = img.crop((350, 380, 900, 600))
    crop.resize((crop.width * 2, crop.height * 2), Image.LANCZOS).save(r"D:\work\_downloads\live_box_check.png")
    print("saved live_box_check.png")
